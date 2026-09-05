import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:local_auth/local_auth.dart';
import '../models/account.dart';
import '../models/investigation.dart';
import '../services/api_service.dart';
import '../widgets/animated_button.dart';
import '../widgets/result_modal.dart';
import 'sar_screen.dart';

class PayScreen extends StatefulWidget {
  final Account sender;
  final Account receiver;
  final List<Account> accounts;

  const PayScreen({
    super.key,
    required this.sender,
    required this.receiver,
    required this.accounts,
  });

  @override
  State<PayScreen> createState() => _PayScreenState();
}

class _PayScreenState extends State<PayScreen> with TickerProviderStateMixin {
  // Mode
  bool _isMuleMode = false;

  // Form Fields
  final TextEditingController _amountController = TextEditingController(text: '0');
  final TextEditingController _descriptionController = TextEditingController();

  // Accounts
  late Account _sender;
  late Account _receiver;

  // Button state
  ButtonState _buttonState = ButtonState.idle;

  // Sliding sheet animation
  late AnimationController _sheetAnimationController;
  late Animation<double> _sheetOffset;

  @override
  void initState() {
    super.initState();
    _sender = widget.sender;
    _receiver = widget.receiver;

    _sheetAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
    _sheetOffset = Tween<double>(begin: 400.0, end: 0.0).animate(
      CurvedAnimation(parent: _sheetAnimationController, curve: Curves.easeOutBack),
    );

    // Slide up sheet after a short delay
    Future.delayed(const Duration(milliseconds: 250), () {
      if (mounted) {
        _sheetAnimationController.forward();
      }
    });
  }

  @override
  void dispose() {
    _amountController.dispose();
    _descriptionController.dispose();
    _sheetAnimationController.dispose();
    super.dispose();
  }

  void _setMuleMode(bool mule) {
    setState(() {
      _isMuleMode = mule;
      if (mule) {
        // Auto-select a mule account as receiver
        final muleAccounts = widget.accounts
            .where((a) => a.riskLevel == RiskLevel.mule)
            .toList();
        if (muleAccounts.isNotEmpty) {
          _receiver = muleAccounts.first;
        }
        _amountController.text = '9900';
        _descriptionController.text = 'Festival gift';
      } else {
        _receiver = widget.receiver;
        _amountController.text = '0';
        _descriptionController.text = '';
      }
    });
  }

  Future<void> _sendPayment() async {
    final String amountStr = _amountController.text;
    if (amountStr == '0' || amountStr.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter an amount')),
      );
      return;
    }

    final double val = double.tryParse(amountStr) ?? 0.0;
    
    // Check sender balance limits
    double senderBal = _sender.balance;
    if (_sender.accountId == 'ACC_GOLD_MOCK') {
      senderBal = 125000.00;
    } else if (_sender.accountId == 'ACC_PLAT_MOCK') {
      senderBal = 45000.00;
    }

    if (val > senderBal) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Insufficient Balance for this card!'),
          backgroundColor: Color(0xFFFF3B30),
        ),
      );
      return;
    }

    // 1. Ask for biometric / fingerprint authorization first
    final bool authenticated = await _authenticateWithBiometrics(val);
    if (!authenticated) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Authentication failed. Transaction cancelled.'),
          backgroundColor: Color(0xFFFF3B30),
        ),
      );
      return;
    }

    setState(() => _buttonState = ButtonState.loading);

    try {
      // Resolve sender account ID dynamically if it is a mock card
      String dbSenderAccountId = _sender.accountId;
      if (dbSenderAccountId == 'ACC_GOLD_MOCK' || dbSenderAccountId == 'ACC_PLAT_MOCK') {
        final prefs = await SharedPreferences.getInstance();
        final realId = prefs.getString('user_selected_account_id');
        if (realId != null && realId.isNotEmpty) {
          dbSenderAccountId = realId;
        } else {
          final fallback = widget.accounts.firstWhere(
            (a) => a.accountId != 'ACC000001' && !a.accountId.toLowerCase().contains('central'),
            orElse: () => widget.accounts.isNotEmpty ? widget.accounts.first : _sender,
          );
          dbSenderAccountId = fallback.accountId;
        }
      }

      // 2. Register transaction in database
      final txnRes = await ApiService().sendTransaction(
        senderAccount: dbSenderAccountId,
        receiverAccount: _receiver.accountId,
        amount: val,
        channel: 'UPI',
        description: _descriptionController.text.isEmpty ? 'P2P Transfer' : _descriptionController.text,
      );

      final String txnId = txnRes['transaction_id']?.toString() ?? 'TXN_ERROR';

      // 2. Start fraud intelligence engine investigation
      final investigationId =
          await ApiService().startInvestigation(txnId, _sender.accountId);

      if (investigationId.isEmpty) {
        throw Exception('No investigation ID returned');
      }

      // Poll until complete
      Investigation? result;
      for (int i = 0; i < 30; i++) {
        await Future.delayed(const Duration(milliseconds: 1200));
        final inv = await ApiService().getInvestigation(investigationId);
        if (!inv.isPending) {
          result = inv;
          break;
        }
      }

      result ??= Investigation.fromJson({
        'investigation_id': investigationId,
        'status': 'completed',
        'final_risk_score': 0.5,
        'final_verdict': 'SUSPICIOUS',
        'explanation_narrative': 'Analysis timed out. Flagged for manual review.',
      });

      setState(() => _buttonState = ButtonState.idle);
      if (!mounted) return;

      showResultModal(
        context: context,
        investigation: result,
        isMuleSimulation: _isMuleMode,
        txnAmount: amountStr,
        txnId: txnId,
        onViewSAR: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => SarScreen(
                investigation: result!,
                sender: _sender,
                txnId: txnId,
                amount: amountStr,
              ),
            ),
          );
        },
      );
    } catch (e) {
      setState(() => _buttonState = ButtonState.idle);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: ${e.toString().replaceAll('Exception: ', '')}'),
          backgroundColor: const Color(0xFFFF3B30),
        ),
      );
    }
  }

  String _formatCurrency(double value) {
    final parts = value.toStringAsFixed(2).split('.');
    String numPart = parts[0];
    String decPart = parts[1];
    
    if (numPart.length <= 3) {
      return '$numPart.$decPart';
    }
    
    String lastThree = numPart.substring(numPart.length - 3);
    String remaining = numPart.substring(0, numPart.length - 3);
    
    List<String> groups = [];
    while (remaining.isNotEmpty) {
      if (remaining.length >= 2) {
        groups.insert(0, remaining.substring(remaining.length - 2));
        remaining = remaining.substring(0, remaining.length - 2);
      } else {
        groups.insert(0, remaining);
        remaining = '';
      }
    }
    
    groups.add(lastThree);
    return '${groups.join(',')}.$decPart';
  }

  @override
  Widget build(BuildContext context) {
    // 1. Resolve selected card parameters
    String cardName = 'Prestige Onyx';
    List<Color> gradientColors = [const Color(0xFF000000), const Color(0xFF2C2C2E)]; // Monochrome card gradient
    String last4 = '0001';
    double balance = _sender.balance;

    if (_sender.accountId == 'ACC_GOLD_MOCK') {
      cardName = 'Prestige Gold';
      gradientColors = [const Color(0xFFC9A84C), const Color(0xFFF5D77A)];
      last4 = '8832';
      balance = 125000.00;
    } else if (_sender.accountId == 'ACC_PLAT_MOCK') {
      cardName = 'Prestige Platinum';
      gradientColors = [const Color(0xFF9B9B9B), const Color(0xFFD4D4D4)];
      last4 = '4289';
      balance = 45000.00;
    } else {
      if (_sender.accountId.length >= 4) {
        last4 = _sender.accountId.substring(_sender.accountId.length - 4);
      }
    }

    return Scaffold(
      backgroundColor: Colors.white, // light mode
      appBar: _buildAppBar(),
      body: Stack(
        children: [
          // Main Scrollable screen area
          Positioned.fill(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.only(left: 20.0, right: 20.0, top: 10.0, bottom: 260.0), // space at bottom for sheet
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Full-width Card Preview
                  _buildCardPreview(cardName, gradientColors),
                  const SizedBox(height: 16),

                  // Available Balance display
                  _buildBalanceDisplay(balance),
                  const SizedBox(height: 24),

                  // Mode simulation toggle
                  _buildModeToggle(),
                  const SizedBox(height: 28),

                  // Transactions List section
                  _buildTransactionsSection(),
                ],
              ),
            ),
          ),

          // Sliding Payment Confirmation Bottom Sheet
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: AnimatedBuilder(
              animation: _sheetOffset,
              builder: (context, child) {
                return Transform.translate(
                  offset: Offset(0, _sheetOffset.value),
                  child: _buildBottomConfirmationSheet(cardName, last4),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: Colors.white,
      elevation: 0,
      scrolledUnderElevation: 0,
      automaticallyImplyLeading: false,
      titleSpacing: 20.0,
      title: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // 'Done' button top-left SF Pro Text Regular 17pt #000000
          GestureDetector(
            onTap: () => Navigator.pop(context),
            child: const Text(
              'Done',
              style: TextStyle(
                fontFamily: 'SF Pro Text',
                color: Color(0xFF000000), // Pure black monochrome Done button
                fontSize: 17,
                fontWeight: FontWeight.normal,
              ),
            ),
          ),
          const Text(
            'Payment Details',
            style: TextStyle(
              fontFamily: 'SF Pro Text',
              color: Colors.black,
              fontSize: 17,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(width: 40),
        ],
      ),
    );
  }

  Widget _buildCardPreview(String cardName, List<Color> colors) {
    return Center(
      child: Container(
        width: double.infinity,
        height: 180, // 180pt height
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20), // 20pt radius
          border: Border.all(color: Colors.black.withOpacity(0.08), width: 0.5),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: colors,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    cardName,
                    style: const TextStyle(
                      fontFamily: 'SF Pro Display',
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Icon(
                    CupertinoIcons.wifi,
                    color: Colors.white,
                    size: 20,
                  ),
                ],
              ),
              const Center(
                child: Text(
                  '•••• •••• •••• 8832',
                  style: TextStyle(
                    fontFamily: 'SF Pro Text',
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 3,
                  ),
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    _sender.customerName.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: 'SF Pro Text',
                      color: Colors.white70,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Text(
                    '12/28',
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      color: Colors.white70,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBalanceDisplay(double balance) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // 'Available Balance' SF Pro Text Regular 15pt #6E6E73
        const Text(
          'Available Balance',
          style: TextStyle(
            fontFamily: 'SF Pro Text',
            fontSize: 15,
            color: Color(0xFF6E6E73),
            fontWeight: FontWeight.normal,
          ),
        ),
        const SizedBox(height: 4),
        // amount SF Pro Display Bold 28pt pure black
        Text(
          '₹${_formatCurrency(balance)}',
          style: const TextStyle(
            fontFamily: 'SF Pro Display',
            fontSize: 28,
            fontWeight: FontWeight.bold,
            color: Colors.black,
          ),
        ),
      ],
    );
  }

  Widget _buildModeToggle() {
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: const Color(0xFFF2F2F7),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          _modeTab('NORMAL', !_isMuleMode, () => _setMuleMode(false)),
          _modeTab('MULE SIMULATOR', _isMuleMode, () => _setMuleMode(true), danger: true),
        ],
      ),
    );
  }

  Widget _modeTab(String label, bool active, VoidCallback onTap, {bool danger = false}) {
    final Color activeColor = danger ? const Color(0xFFFF3B30) : const Color(0xFF000000); // Monochrome Black tint
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color: active ? Colors.white : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            boxShadow: active
                ? const [
                    BoxShadow(
                      color: Color(0x14000000),
                      blurRadius: 4,
                      offset: Offset(0, 2),
                    ),
                  ]
                : null,
            border: active ? Border.all(color: activeColor.withOpacity(0.15), width: 0.5) : null,
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontFamily: 'SF Pro Text',
                color: active ? activeColor : const Color(0xFF6E6E73),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTransactionsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // header 'Latest Transactions' SF Pro Text Semibold 17pt
        const Text(
          'Latest Transactions',
          style: TextStyle(
            fontFamily: 'SF Pro Text',
            fontSize: 17,
            fontWeight: FontWeight.w600,
            color: Colors.black,
          ),
        ),
        const SizedBox(height: 12),
        ListView(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          padding: EdgeInsets.zero,
          children: [
            _buildTxnRow(
              icon: CupertinoIcons.shopping_cart,
              merchant: 'Apple Store',
              date: 'Today, 10:24 AM',
              amount: '-₹8,500.00',
              isCredit: false,
            ),
            _buildTxnRow(
              icon: CupertinoIcons.cart_fill,
              merchant: 'Starbucks Coffee',
              date: 'Yesterday',
              amount: '-₹350.00',
              isCredit: false,
            ),
            _buildTxnRow(
              icon: CupertinoIcons.money_dollar_circle_fill,
              merchant: 'Salary Deposit',
              date: 'May 25, 2026',
              amount: '+₹1,15,000.00',
              isCredit: true,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildTxnRow({
    required IconData icon,
    required String merchant,
    required String date,
    required String amount,
    required bool isCredit,
  }) {
    return Container(
      height: 60,
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: Color(0xFFE5E5EA), width: 0.5)),
      ),
      child: Row(
        children: [
          // 36pt rounded square category icon
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFFF2F2F7),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: const Color(0xFF000000), size: 18), // Monochrome active black
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  merchant,
                  style: const TextStyle(
                    fontFamily: 'SF Pro Text',
                    color: Colors.black,
                    fontSize: 17,
                    fontWeight: FontWeight.normal,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  date,
                  style: const TextStyle(
                    fontFamily: 'SF Pro Text',
                    color: Color(0xFF6E6E73),
                    fontSize: 13,
                    fontWeight: FontWeight.normal,
                  ),
                ),
              ],
            ),
          ),
          // amount (black for both credits & debits in monochrome theme style)
          Text(
            amount,
            style: TextStyle(
              fontFamily: 'SF Pro Text',
              color: isCredit ? const Color(0xFF000000) : Colors.black, // Monochrome black for credits
              fontSize: 17,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomConfirmationSheet(String cardName, String last4) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(
            color: Color(0x1F000000),
            blurRadius: 20,
            offset: Offset(0, -5),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 12pt top drag handle
              Center(
                child: Container(
                  width: 36,
                  height: 5,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE5E5EA),
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              const Center(
                child: Text(
                  'Sentinel Pay',
                  style: TextStyle(
                    fontFamily: 'SF Pro Text',
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF6E6E73),
                    letterSpacing: 1.0,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFF2F2F7), // secondary action Apple tint background #F2F2F7
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Payment Method',
                          style: TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 13,
                            color: Color(0xFF6E6E73),
                          ),
                        ),
                        Text(
                          '$cardName •••• $last4',
                          style: const TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 13,
                            color: Colors.black,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Receiver',
                          style: TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 13,
                            color: Color(0xFF6E6E73),
                          ),
                        ),
                        Text(
                          _receiver.customerName,
                          style: const TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 13,
                            color: Colors.black,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Divider(color: Color(0xFFE5E5EA), height: 1),
                    const SizedBox(height: 16),

                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Amount',
                          style: TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: Colors.black,
                          ),
                        ),
                        SizedBox(
                          width: 140,
                          height: 36,
                          child: TextField(
                            controller: _amountController,
                            keyboardType: TextInputType.number,
                            textAlign: TextAlign.end,
                            style: const TextStyle(
                              fontFamily: 'SF Pro Display',
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                              color: Colors.black,
                            ),
                            decoration: const InputDecoration(
                              prefixText: '₹',
                              prefixStyle: TextStyle(
                                  fontFamily: 'SF Pro Display',
                                  fontSize: 22,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.black),
                              border: InputBorder.none,
                              contentPadding: EdgeInsets.zero,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Note',
                          style: TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 13,
                            color: Color(0xFF6E6E73),
                          ),
                        ),
                        SizedBox(
                          width: 160,
                          height: 30,
                          child: TextField(
                            controller: _descriptionController,
                            textAlign: TextAlign.end,
                            style: const TextStyle(
                              fontFamily: 'SF Pro Text',
                              fontSize: 13,
                              color: Colors.black,
                            ),
                            decoration: const InputDecoration(
                              hintText: 'Add description...',
                              hintStyle: TextStyle(color: Color(0xFFC7C7CC)),
                              border: InputBorder.none,
                              contentPadding: EdgeInsets.zero,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Confirm Payment Action Button (Pill shape, #000000 background)
              AnimatedSendButton(
                state: _buttonState,
                idleLabel: 'Confirm Payment',
                onPressed: _sendPayment,
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }

  Future<bool> _authenticateWithBiometrics(double amount) async {
    final LocalAuthentication auth = LocalAuthentication();
    try {
      final bool canAuthenticateWithBiometrics = await auth.canCheckBiometrics;
      final bool canAuthenticate = canAuthenticateWithBiometrics || await auth.isDeviceSupported();

      if (!canAuthenticate) {
        return await _showMockBiometricDialog(amount);
      }

      final bool didAuthenticate = await auth.authenticate(
        localizedReason: 'Scan fingerprint to confirm payment of ₹${_formatCurrency(amount)}',
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
      return didAuthenticate;
    } catch (e) {
      print("Local auth error: $e");
      return await _showMockBiometricDialog(amount);
    }
  }

  Future<bool> _showMockBiometricDialog(double amount) async {
    bool authenticated = false;
    await showCupertinoModalPopup<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Center(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 40),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 30),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.15),
                      blurRadius: 24,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        CupertinoIcons.lock_shield,
                        color: Color(0xFF000000),
                        size: 44,
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Security Verification',
                        style: TextStyle(
                          fontFamily: 'SF Pro Display',
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Colors.black,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Scan fingerprint to authorize payment of ₹${_formatCurrency(amount)}',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontFamily: 'SF Pro Text',
                          fontSize: 14,
                          color: Color(0xFF6E6E73),
                        ),
                      ),
                      const SizedBox(height: 32),
                      
                      GestureDetector(
                        onTap: () {
                          setModalState(() {
                            authenticated = true;
                          });
                          HapticFeedback.heavyImpact();
                          Navigator.pop(context);
                        },
                        child: Container(
                          width: 80,
                          height: 80,
                          decoration: BoxDecoration(
                            color: const Color(0xFFF2F2F7),
                            shape: BoxShape.circle,
                            border: Border.all(color: const Color(0xFFE5E5EA), width: 1),
                          ),
                          child: const Center(
                            child: Icon(
                              Icons.fingerprint,
                              color: Color(0xFF000000),
                              size: 48,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Tap fingerprint to verify',
                        style: TextStyle(
                          fontFamily: 'SF Pro Text',
                          fontSize: 12,
                          color: Color(0xFF8E8E93),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 24),
                      TextButton(
                        onPressed: () {
                          authenticated = false;
                          Navigator.pop(context);
                        },
                        child: const Text(
                          'Cancel',
                          style: TextStyle(
                            fontFamily: 'SF Pro Text',
                            color: Color(0xFFFF3B30),
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
    return authenticated;
  }
}
