import 'dart:async';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/account.dart';
import '../models/transaction.dart';
import '../services/api_service.dart';
import 'pay_screen.dart';
import 'settings_screen.dart';
import 'onboarding_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isRegistered = false;
  bool _loading = true;

  // Profile data
  String _name = '';
  String _upiId = '';
  String _role = 'sender'; // 'sender' or 'receiver'
  String _linkedAccountId = '';

  List<Account> _accounts = [];
  Account? _userAccount;
  List<Account> _otherAccounts = [];

  // Card deck state
  bool _isFannedOut = false;
  int? _activeCardIndex; // null = combined balance card, 0 = Gold, 1 = Platinum, 2 = Emerald (Linked Active BOI)

  // Receiver Mode poll timer
  Timer? _pollTimer;
  int _lastTxnCount = 0;

  @override
  void initState() {
    super.initState();
    _checkRegistration();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _checkRegistration() async {
    final prefs = await SharedPreferences.getInstance();
    final registered = prefs.getBool('user_registered') ?? false;
    if (registered) {
      setState(() {
        _isRegistered = true;
        _name = prefs.getString('user_name') ?? '';
        _upiId = prefs.getString('user_upi_id') ?? '';
        _role = prefs.getString('user_role') ?? 'sender';
        _linkedAccountId = prefs.getString('user_selected_account_id') ?? '';
      });
      await _loadData();
      if (_role == 'receiver') {
        _startReceiverPolling();
      }
    } else {
      setState(() {
        _isRegistered = false;
        _loading = false;
      });
    }
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final accounts = await ApiService().fetchAccounts(limit: 50);
      
      // Find our linked account
      Account? linked;
      final others = <Account>[];
      for (final acc in accounts) {
        if (acc.accountId == _linkedAccountId) {
          linked = acc;
        } else {
          others.add(acc);
        }
      }

      // Fallback if not found: find the first non-system/non-settlement account
      linked ??= accounts.firstWhere(
        (acc) {
          final id = acc.accountId.toLowerCase();
          final name = acc.customerName.toLowerCase();
          return !id.contains('central') &&
              !name.contains('central') &&
              !id.contains('settlement') &&
              !name.contains('settlement') &&
              id != 'acc000001';
        },
        orElse: () => accounts.isNotEmpty ? accounts.first : Account(accountId: '', customerName: '', riskProfile: '', raw: {}),
      );

      setState(() {
        _accounts = accounts;
        _userAccount = linked;
        _otherAccounts = others;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  // --- RECEIVER REAL-TIME TRANSACTION LISTENING ---
  void _startReceiverPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      try {
        final txns = await ApiService().fetchTransactions(limit: 50);
        // Find transactions specifically sent to us
        final received = txns.where((t) => t.receiverId == _linkedAccountId).toList();
        
        if (received.length > _lastTxnCount && _lastTxnCount != 0) {
          // New payment detected! Trigger notification modal
          final latest = received.first;
          _triggerPaymentAlert(latest);
        }
        _lastTxnCount = received.length;
      } catch (_) {}
    });
  }

  void _triggerPaymentAlert(Transaction txn) {
    HapticFeedback.heavyImpact();
    
    // Find sender detail
    final senderName = _accounts.firstWhere((a) => a.accountId == txn.senderId, orElse: () => _accounts.first).customerName;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(CupertinoIcons.check_mark_circled_solid, color: Color(0xFF000000), size: 28),
            const SizedBox(width: 8),
            Text('Payment Received', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 16),
            Text(
              '₹${_formatCurrency(txn.amount)}',
              style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: Colors.black),
            ),
            const SizedBox(height: 8),
            Text('From: $senderName', style: const TextStyle(color: Color(0xFF6E6E73))),
            Text('ID: ${txn.transactionId}', style: const TextStyle(fontSize: 10, color: Color(0xFF8E8E93))),
            const SizedBox(height: 12),
          ],
        ),
        actions: [
          CupertinoDialogAction(
            child: const Text('Dismiss', style: TextStyle(color: Color(0xFF000000))),
            onPressed: () {
              Navigator.pop(ctx);
              _loadData(); // refresh balance
            },
          )
        ],
      ),
    );
  }

  void _toggleFan() {
    HapticFeedback.mediumImpact();
    setState(() {
      _isFannedOut = !_isFannedOut;
      if (!_isFannedOut) {
        _activeCardIndex = null;
      }
    });
  }

  void _selectCard(int index) {
    HapticFeedback.lightImpact();
    setState(() {
      if (_activeCardIndex == index) {
        _activeCardIndex = null; // collapse
      } else {
        _activeCardIndex = index;
      }
    });
  }

  void _resetProfile() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    _pollTimer?.cancel();
    setState(() {
      _isRegistered = false;
      _accounts = [];
      _userAccount = null;
      _isFannedOut = false;
      _activeCardIndex = null;
    });
    _checkRegistration();
  }

  String _getInitials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || name.isEmpty) return 'US';
    if (parts.length == 1) {
      return parts[0].substring(0, parts[0].length >= 2 ? 2 : 1).toUpperCase();
    }
    return (parts[0][0] + parts[1][0]).toUpperCase();
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
    if (!_isRegistered) {
      return OnboardingScreen(onComplete: _checkRegistration);
    }

    if (_loading) {
      return const Scaffold(
        backgroundColor: Colors.white,
        body: Center(child: CupertinoActivityIndicator(color: Color(0xFF000000), radius: 14)),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFFFFFFFF), // Apple systemBackground white
      appBar: _buildAppBar(),
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0), // 20pt side margins
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 16),
              
              // 3-Card Stack with Apple Wallet exact fan-out/peek animation
              _buildCardStack(),
              
              const SizedBox(height: 16),
              
              // Apple Cash styled summary card
              _buildSummaryCard(),
              
              const SizedBox(height: 32),
              
              // Role-based panels
              _role == 'sender' ? _buildRecipientsPanel() : _buildReceiverPanel(),
              
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: Colors.white,
      elevation: 0,
      scrolledUnderElevation: 0,
      automaticallyImplyLeading: false,
      titleSpacing: 20.0, // align nicely with side margins
      title: Row(
        children: [
          // User avatar 32pt circle left
          Container(
            width: 32,
            height: 32,
            decoration: const BoxDecoration(
              color: Color(0xFFF2F2F7),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                _getInitials(_name),
                style: const TextStyle(
                  fontFamily: 'SF Pro Rounded',
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF000000),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                _name.isNotEmpty ? _name.toUpperCase() : 'CUSTOMER 7',
                style: const TextStyle(
                  fontFamily: 'SF Pro Text',
                  color: Color(0xFF6E6E73),
                  fontSize: 11,
                  fontWeight: FontWeight.normal,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 1),
              const Text(
                'Sentinel Pay',
                style: TextStyle(
                  fontFamily: 'SF Pro Display',
                  color: Colors.black,
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        IconButton(
          icon: const Icon(CupertinoIcons.gear_alt_fill, color: Color(0xFF6E6E73), size: 22),
          onPressed: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const SettingsScreen()),
          ).then((_) => _loadData()),
        ),
        IconButton(
          icon: const Icon(CupertinoIcons.power, color: Color(0xFFFF3B30), size: 22),
          onPressed: () {
            showCupertinoDialog(
              context: context,
              builder: (ctx) => CupertinoAlertDialog(
                title: const Text('Reset Demo Profile?'),
                content: const Text('This will clear your local registered profile and linked cards.'),
                actions: [
                  CupertinoDialogAction(
                    isDestructiveAction: true,
                    child: const Text('Reset'),
                    onPressed: () {
                      Navigator.pop(ctx);
                      _resetProfile();
                    },
                  ),
                  CupertinoDialogAction(
                    child: const Text('Cancel'),
                    onPressed: () => Navigator.pop(ctx),
                  )
                ],
              ),
            );
          },
        ),
        const SizedBox(width: 8),
      ],
    );
  }

  // --- HIGH FIDELITY INTERACTIVE CARD STACK ---
  Widget _buildCardStack() {
    return Center(
      child: GestureDetector(
        onTap: _toggleFan,
        child: Container(
          width: 310,
          height: 320,
          color: Colors.transparent,
          child: Stack(
            clipBehavior: Clip.none,
            children: _buildAnimatedCards(),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildAnimatedCards() {
    // Resting vs Fanned top offsets
    double goldTop = 0;
    double platTop = 60;
    double emerTop = 120;
    
    double goldScale = 1.0;
    double platScale = 0.96;
    double emerScale = 0.92;
    
    int goldZ = 0;
    int platZ = 1;
    int emerZ = 2;

    if (_isFannedOut) {
      goldTop = 0;
      platTop = 80;
      emerTop = 160;
      
      goldScale = 1.0;
      platScale = 1.0;
      emerScale = 1.0;
      
      if (_activeCardIndex == 0) {
        goldTop = -20;
        platTop = 160;
        emerTop = 185;
        goldScale = 1.03;
        
        goldZ = 2;
        platZ = 0;
        emerZ = 1;
      } else if (_activeCardIndex == 1) {
        platTop = -20;
        goldTop = 160;
        emerTop = 185;
        platScale = 1.03;
        
        platZ = 2;
        goldZ = 0;
        emerZ = 1;
      } else if (_activeCardIndex == 2) {
        emerTop = -20;
        goldTop = 160;
        platTop = 185;
        emerScale = 1.03;
        
        emerZ = 2;
        goldZ = 0;
        platZ = 1;
      }
    } else {
      goldTop = 0;
      platTop = 60;
      emerTop = 120;
      
      goldScale = 1.0;
      platScale = 0.96;
      emerScale = 0.92;
    }

    final cardGold = AnimatedPositioned(
      key: const ValueKey('gold'),
      duration: const Duration(milliseconds: 350),
      curve: Curves.easeOutBack,
      top: goldTop,
      left: 0,
      right: 0,
      child: AnimatedScale(
        duration: const Duration(milliseconds: 250),
        scale: goldScale,
        child: _buildCard(
          name: 'Prestige Gold',
          gradientColors: const [Color(0xFFC9A84C), Color(0xFFF5D77A)],
          number: '•••• •••• •••• 8832',
          holder: _name.isNotEmpty ? _name : 'ALEXANDER HAMILTON',
          expiry: '09/29',
          onTap: () {
            if (!_isFannedOut) {
              _toggleFan();
            } else {
              _selectCard(0);
            }
          },
        ),
      ),
    );

    final cardPlat = AnimatedPositioned(
      key: const ValueKey('plat'),
      duration: const Duration(milliseconds: 350),
      curve: Curves.easeOutBack,
      top: platTop,
      left: 0,
      right: 0,
      child: AnimatedScale(
        duration: const Duration(milliseconds: 250),
        scale: platScale,
        child: _buildCard(
          name: 'Prestige Platinum',
          gradientColors: const [Color(0xFF9B9B9B), Color(0xFFD4D4D4)],
          number: '•••• •••• •••• 4289',
          holder: _name.isNotEmpty ? _name : 'ALEXANDER HAMILTON',
          expiry: '12/28',
          onTap: () {
            if (!_isFannedOut) {
              _toggleFan();
            } else {
              _selectCard(1);
            }
          },
        ),
      ),
    );

    final cardEmer = AnimatedPositioned(
      key: const ValueKey('emer'),
      duration: const Duration(milliseconds: 350),
      curve: Curves.easeOutBack,
      top: emerTop,
      left: 0,
      right: 0,
      child: AnimatedScale(
        duration: const Duration(milliseconds: 250),
        scale: emerScale,
        child: _buildCard(
          name: 'Prestige Emerald',
          gradientColors: const [Color(0xFF1B4D3E), Color(0xFF0D2D23)],
          number: _userAccount != null ? _userAccount!.accountId : '•••• •••• •••• 0001',
          holder: _name.isNotEmpty ? _name : 'ALEXANDER HAMILTON',
          expiry: '05/30',
          onTap: () {
            if (!_isFannedOut) {
              _toggleFan();
            } else {
              _selectCard(2);
            }
          },
        ),
      ),
    );

    final entries = [
      _ZEntry(widget: cardGold, z: goldZ),
      _ZEntry(widget: cardPlat, z: platZ),
      _ZEntry(widget: cardEmer, z: emerZ),
    ];
    entries.sort((a, b) => a.z.compareTo(b.z));

    return entries.map((e) => e.widget).toList();
  }

  Widget _buildCard({
    required String name,
    required List<Color> gradientColors,
    required String number,
    required String holder,
    required String expiry,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: 310,
        height: 180, // 180pt height
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20), // 20pt radius
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 0.5),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: gradientColors,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 10,
              offset: const Offset(0, 4),
            )
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
                    name,
                    style: const TextStyle(
                      fontFamily: 'SF Pro Display',
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const Icon(
                    CupertinoIcons.wifi, // contactless icon top-right in white
                    color: Colors.white,
                    size: 20,
                  ),
                ],
              ),
              Center(
                child: Text(
                  number,
                  style: const TextStyle(
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
                    holder.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: 'SF Pro Text',
                      color: Colors.white70,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Text(
                    expiry,
                    style: const TextStyle(
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

  // --- APPLE CASH STYLE SUMMARY CARD ---
  Widget _buildSummaryCard() {
    String label = 'TOTAL COMBINED BALANCE';
    double balance = 125000.00 + 45000.00 + (_userAccount?.balance ?? 0.0);
    
    if (_activeCardIndex == 0) {
      label = 'PRESTIGE GOLD BALANCE';
      balance = 125000.00;
    } else if (_activeCardIndex == 1) {
      label = 'PRESTIGE PLATINUM BALANCE';
      balance = 45000.00;
    } else if (_activeCardIndex == 2) {
      label = 'PRESTIGE EMERALD BALANCE';
      balance = _userAccount?.balance ?? 0.0;
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 20.0, horizontal: 16.0),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E), // #1C1C1E dark background
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // 'TOTAL COMBINED BALANCE' SF Pro Text Regular 12pt #8E8E93
          Text(
            label,
            style: const TextStyle(
              fontFamily: 'SF Pro Text',
              fontSize: 12,
              fontWeight: FontWeight.normal,
              color: Color(0xFF8E8E93),
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 8),
          // balance '₹1,25,000.00' SF Pro Display Bold 32pt white
          Text(
            '₹${_formatCurrency(balance)}',
            style: const TextStyle(
              fontFamily: 'SF Pro Display',
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 8),
          // 'TAP CARDS TO CHOOSE' SF Pro Text Regular 11pt #636366
          const Text(
            'TAP CARDS TO CHOOSE',
            style: TextStyle(
              fontFamily: 'SF Pro Text',
              fontSize: 11,
              fontWeight: FontWeight.normal,
              color: Color(0xFF636366),
              letterSpacing: 1.0,
            ),
          ),
        ],
      ),
    );
  }

  // --- DYNAMIC RECIPIENTS PANEL ---
  Widget _buildRecipientsPanel() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 'Dynamic Recipients' SF Pro Text Semibold 15pt #6E6E73
        const Text(
          'Dynamic Recipients',
          style: TextStyle(
            fontFamily: 'SF Pro Text',
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: Color(0xFF6E6E73),
          ),
        ),
        const SizedBox(height: 12),
        // Recipient grid: horizontal scroll, each recipient tile 80x95pt
        SizedBox(
          height: 98,
          child: _otherAccounts.isEmpty
              ? const Center(
                  child: Text(
                    'No recipients found in laptop DB.',
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      color: Color(0xFF6E6E73),
                      fontSize: 13,
                    ),
                  ),
                )
              : ListView.separated(
                  scrollDirection: Axis.horizontal,
                  physics: const BouncingScrollPhysics(),
                  itemCount: _otherAccounts.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                  itemBuilder: (context, i) {
                    final acc = _otherAccounts[i];
                    return GestureDetector(
                      onTap: () {
                        if (_userAccount == null) return;
                        HapticFeedback.selectionClick();
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => PayScreen(
                              sender: _activeCardIndex == 0 
                                  ? Account(
                                      accountId: 'ACC_GOLD_MOCK',
                                      customerName: _name.isNotEmpty ? _name : 'Prestige Gold',
                                      riskProfile: 'CLEAN',
                                      raw: const {'balance': 125000.00},
                                    )
                                  : _activeCardIndex == 1
                                      ? Account(
                                          accountId: 'ACC_PLAT_MOCK',
                                          customerName: _name.isNotEmpty ? _name : 'Prestige Platinum',
                                          riskProfile: 'CLEAN',
                                          raw: const {'balance': 45000.00},
                                        )
                                      : _userAccount!,
                              receiver: acc,
                              accounts: _accounts,
                            ),
                          ),
                        ).then((_) => _loadData());
                      },
                      child: Container(
                        width: 80,
                        height: 95, // 80x95pt size
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12), // 12pt radius
                          border: Border.all(
                            color: const Color(0xFFE5E5EA),
                            width: 0.5,
                          ),
                          boxShadow: const [
                            BoxShadow(
                              color: Color(0x0A000000),
                              blurRadius: 4,
                              offset: Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            // 44x44pt green avatar
                            Container(
                              width: 44,
                              height: 44,
                              decoration: const BoxDecoration(
                                color: Color(0xFFF2F2F7), // gray background
                                shape: BoxShape.circle,
                              ),
                              child: Center(
                                child: Text(
                                  _getInitials(acc.customerName),
                                  style: const TextStyle(
                                    fontFamily: 'SF Pro Rounded',
                                    color: Color(0xFF000000), // active monochrome text
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(height: 8),
                            // name SF Pro Text Regular 12pt
                            Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 4.0),
                              child: Text(
                                acc.customerName.split(' ').first,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontFamily: 'SF Pro Text',
                                  color: Colors.black,
                                  fontSize: 12,
                                  fontWeight: FontWeight.normal,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  // --- RECEIVER ACTIVE PANEL (Scan QR) ---
  Widget _buildReceiverPanel() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Receive Payments (Scan QR)',
          style: TextStyle(
            fontFamily: 'SF Pro Text',
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: Color(0xFF6E6E73),
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: const Color(0xFFF2F2F7), // light grouped background
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
          ),
          child: Column(
            children: [
              // Premium simulated QR code
              Container(
                width: 180,
                height: 180,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x0F000000),
                      blurRadius: 10,
                      offset: Offset(0, 4),
                    ),
                  ],
                ),
                child: Image.network(
                  'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=upi://pay?pa=$_upiId&pn=$_name&mc=0000&mode=02&purpose=00',
                  loadingBuilder: (context, child, loadingProgress) {
                    if (loadingProgress == null) return child;
                    return const Center(child: CupertinoActivityIndicator(color: Color(0xFF000000)));
                  },
                  errorBuilder: (_, __, ___) => const Icon(CupertinoIcons.qrcode, color: Colors.black, size: 80),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                _name,
                style: const TextStyle(
                  fontFamily: 'SF Pro Text',
                  color: Colors.black,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _upiId,
                style: const TextStyle(
                  fontFamily: 'SF Pro Rounded',
                  color: Color(0xFF000000),
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 20),
              const Divider(color: Color(0xFFE5E5EA)),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  CupertinoActivityIndicator(color: Color(0xFF000000), radius: 6),
                  SizedBox(width: 8),
                  Text(
                    'Listening live for incoming transactions...',
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      color: Color(0xFF6E6E73),
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              )
            ],
          ),
        ),
      ],
    );
  }
}

class _ZEntry {
  final Widget widget;
  final int z;
  const _ZEntry({required this.widget, required this.z});
}
