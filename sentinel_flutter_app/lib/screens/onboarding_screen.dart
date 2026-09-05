import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/account.dart';
import '../services/api_service.dart';

class OnboardingScreen extends StatefulWidget {
  final VoidCallback? onComplete;

  const OnboardingScreen({super.key, this.onComplete});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  // Form controllers
  late final TextEditingController _nameController;
  late final TextEditingController _mobileController;
  late final TextEditingController _upiIdController;

  // Form states
  String _name = '';
  String _mobile = '';
  String _upiId = '';
  String _role = 'sender'; // 'sender' or 'receiver'
  Account? _linkedAccount;

  List<Account> _accounts = [];
  bool _loadingAccounts = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _mobileController = TextEditingController();
    _upiIdController = TextEditingController();

    _nameController.addListener(() {
      setState(() => _name = _nameController.text);
    });
    _mobileController.addListener(() {
      setState(() => _mobile = _mobileController.text);
    });
    _upiIdController.addListener(() {
      setState(() => _upiId = _upiIdController.text);
    });

    _loadAccounts();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _mobileController.dispose();
    _upiIdController.dispose();
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadAccounts() async {
    setState(() {
      _loadingAccounts = true;
      _error = null;
    });
    try {
      final accounts = await ApiService().fetchAccounts(limit: 50);
      final filteredAccounts = accounts.where((acc) {
        final id = acc.accountId.toLowerCase();
        final name = acc.customerName.toLowerCase();
        return !id.contains('central') &&
            !name.contains('central') &&
            !id.contains('settlement') &&
            !name.contains('settlement') &&
            id != 'acc000001';
      }).toList();
      setState(() {
        _accounts = filteredAccounts;
        _loadingAccounts = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loadingAccounts = false;
      });
    }
  }

  Future<void> _saveProfile() async {
    if (_linkedAccount == null) return;
    
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('user_registered', true);
    await prefs.setString('user_name', _name.isEmpty ? _linkedAccount!.customerName : _name);
    await prefs.setString('user_mobile', _mobile.isEmpty ? '9876543210' : _mobile);
    await prefs.setString('user_upi_id', _upiId.isEmpty ? '${_linkedAccount!.accountId.toLowerCase()}@boi' : _upiId);
    await prefs.setString('user_role', _role);
    await prefs.setString('user_selected_account_id', _linkedAccount!.accountId);
    
    // Restore navigation bar styling
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        systemNavigationBarColor: Colors.white,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
    );
    
    if (widget.onComplete != null) {
      widget.onComplete!();
    } else {
      // If we are pushed onto main stack, pop back to home
      Navigator.pushReplacementNamed(context, '/home');
    }
  }

  @override
  Widget build(BuildContext context) {
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        statusBarBrightness: Brightness.light,
        systemNavigationBarColor: Colors.white,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
    );

    return Scaffold(
      backgroundColor: const Color(0xFFFFFFFF), // pure white systemBackground
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: PageView(
                controller: _pageController,
                physics: const NeverScrollableScrollPhysics(),
                onPageChanged: (page) => setState(() => _currentPage = page),
                children: [
                  _buildWelcomePage(),
                  _buildProfilePage(),
                  _buildLinkCardPage(),
                ],
              ),
            ),
            _buildNavigationFooter(),
          ],
        ),
      ),
    );
  }

  Widget _buildWelcomePage() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const Spacer(flex: 3),
          // Shield Icon centered in a 96x96pt circular glyph container
          Container(
            width: 96,
            height: 96,
            decoration: const BoxDecoration(
              color: Color(0xFFF2F2F7), // soft #F2F2F7
              shape: BoxShape.circle,
            ),
            child: const Center(
              child: Icon(
                CupertinoIcons.shield_fill,
                size: 48,
                color: Color(0xFF000000), // Pure black monochrome shield
              ),
            ),
          ),
          const SizedBox(height: 32),
          // Title "GARUDA SENTINEL" in SF Pro Display Bold 34pt
          const Text(
            'GARUDA SENTINEL',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: 'SF Pro Display',
              fontSize: 34,
              fontWeight: FontWeight.bold,
              color: Colors.black,
              letterSpacing: 0.38,
            ),
          ),
          const SizedBox(height: 8),
          // Subtitle in SF Pro Text Regular 17pt, #6E6E73
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 24.0),
            child: Text(
              'BOI Fraud & P2P Intelligence Platform',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: 'SF Pro Text',
                fontSize: 17,
                fontWeight: FontWeight.normal,
                color: Color(0xFF6E6E73), // secondary label color
                letterSpacing: -0.41,
              ),
            ),
          ),
          const Spacer(flex: 2),
          // Three feature rows in Apple's App Store feature highlights
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12.0),
            child: Column(
              children: [
                _featureRow(
                  CupertinoIcons.lock_shield,
                  'Core Security Shield',
                  'Anti-fraud validation direct from COBOL and AI Layers.',
                ),
                const SizedBox(height: 24),
                _featureRow(
                  CupertinoIcons.device_phone_portrait,
                  'Multi-Device Simulation',
                  'Simulate dynamic Sender & Receiver transactions in real-time.',
                ),
                const SizedBox(height: 24),
                _featureRow(
                  CupertinoIcons.bolt_fill,
                  'Integrated Ecosystem',
                  'All transactions execute and settle on your laptop live database.',
                ),
              ],
            ),
          ),
          const Spacer(flex: 4),
        ],
      ),
    );
  }

  // App Store listing style feature highlight row
  Widget _featureRow(IconData icon, String title, String desc) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 28x28pt rounded square container in #F2F2F7
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: const Color(0xFFF2F2F7), // Tinted glass style secondary Action
            borderRadius: BorderRadius.circular(6),
          ),
          child: Center(
            child: Icon(
              icon,
              color: const Color(0xFF000000), // Monochrome active black
              size: 16,
            ),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Title in SF Pro Text Semibold 17pt pure black
              Text(
                title,
                style: const TextStyle(
                  fontFamily: 'SF Pro Text',
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  color: Colors.black,
                  letterSpacing: -0.41,
                ),
              ),
              const SizedBox(height: 2),
              // Subtitle in SF Pro Text Regular 15pt #6E6E73
              Text(
                desc,
                style: const TextStyle(
                  fontFamily: 'SF Pro Text',
                  fontSize: 15,
                  fontWeight: FontWeight.normal,
                  color: Color(0xFF6E6E73),
                  height: 1.3,
                  letterSpacing: -0.24,
                ),
              ),
            ],
          ),
        )
      ],
    );
  }

  Widget _buildProfilePage() {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 20),
          // Large title "Profile Setup" in SF Pro Display Bold 34pt
          const Text(
            'Profile Setup',
            style: TextStyle(
              fontFamily: 'SF Pro Display',
              fontSize: 34,
              fontWeight: FontWeight.bold,
              color: Colors.black,
              letterSpacing: 0.38,
            ),
          ),
          const SizedBox(height: 8),
          // Subtitle in SF Pro Text Regular 17pt #6E6E73
          const Text(
            'Configure your credentials and operating role.',
            style: TextStyle(
              fontFamily: 'SF Pro Text',
              fontSize: 17,
              fontWeight: FontWeight.normal,
              color: Color(0xFF6E6E73),
              letterSpacing: -0.41,
            ),
          ),
          const SizedBox(height: 24),
          
          // Inset UITableView card: #FFFFFF, 12pt radius, #E5E5EA 0.5px border
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: const Color(0xFFE5E5EA),
                width: 0.5,
              ),
            ),
            child: Column(
              children: [
                _buildFormRow(
                  label: 'Full Name',
                  hint: 'Enter full name',
                  controller: _nameController,
                  icon: CupertinoIcons.person_fill,
                ),
                const Divider(
                  height: 0.5,
                  thickness: 0.5,
                  color: Color(0xFFE5E5EA),
                  indent: 52,
                ),
                _buildFormRow(
                  label: 'Mobile Number',
                  hint: 'Enter mobile number',
                  controller: _mobileController,
                  icon: CupertinoIcons.phone_fill,
                  keyboardType: TextInputType.phone,
                ),
                const Divider(
                  height: 0.5,
                  thickness: 0.5,
                  color: Color(0xFFE5E5EA),
                  indent: 52,
                ),
                _buildFormRow(
                  label: 'UPI ID',
                  hint: 'example@boi',
                  controller: _upiIdController,
                  icon: null,
                  isRupeeIcon: true,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          
          // Section label in SF Pro Text Medium 13pt #6E6E73 uppercase
          _sectionHeader('OPERATING MODE'),
          const SizedBox(height: 8),
          
          // Segmented control in Apple's native style
          SizedBox(
            width: double.infinity,
            child: CupertinoSlidingSegmentedControl<String>(
              groupValue: _role,
              backgroundColor: const Color(0xFFF2F2F7),
              thumbColor: Colors.white,
              children: {
                'sender': Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  child: Text(
                    'SENDER',
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: _role == 'sender' ? Colors.black : const Color(0xFF6E6E73),
                    ),
                  ),
                ),
                'receiver': Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  child: Text(
                    'RECEIVER',
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: _role == 'receiver' ? Colors.black : const Color(0xFF6E6E73),
                    ),
                  ),
                ),
              },
              onValueChanged: (value) {
                if (value != null) {
                  setState(() => _role = value);
                }
              },
            ),
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildFormRow({
    required String label,
    required String hint,
    required TextEditingController controller,
    IconData? icon,
    bool isRupeeIcon = false,
    TextInputType keyboardType = TextInputType.text,
  }) {
    return Container(
      height: 44, // 44pt row height
      padding: const EdgeInsets.symmetric(horizontal: 16.0),
      child: Row(
        children: [
          // Leading icon in pure black #000000
          SizedBox(
            width: 24,
            height: 24,
            child: Center(
              child: isRupeeIcon
                  ? Container(
                      width: 20,
                      height: 20,
                      decoration: const BoxDecoration(
                        color: Color(0xFF000000), // pure black
                        shape: BoxShape.circle,
                      ),
                      child: const Center(
                        child: Text(
                          '₹',
                          style: TextStyle(
                            fontFamily: 'SF Pro Text',
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    )
                  : Icon(
                      icon,
                      color: const Color(0xFF000000), // pure black
                      size: 20,
                    ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Floating label in SF Pro Text Medium 13pt #6E6E73
                Text(
                  label,
                  style: const TextStyle(
                    fontFamily: 'SF Pro Text',
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFF6E6E73),
                  ),
                ),
                Expanded(
                  child: TextField(
                    controller: controller,
                    keyboardType: keyboardType,
                    style: const TextStyle(
                      fontFamily: 'SF Pro Text',
                      fontSize: 15,
                      color: Colors.black,
                    ),
                    decoration: InputDecoration(
                      hintText: hint,
                      hintStyle: const TextStyle(
                        fontFamily: 'SF Pro Text',
                        fontSize: 15,
                        color: Color(0xFFAEAEB2),
                      ),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.zero,
                      isDense: true,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLinkCardPage() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 20),
          // Large title 'Link Bank Account' SF Pro Display Bold 34pt
          const Text(
            'Link Bank Account',
            style: TextStyle(
              fontFamily: 'SF Pro Display',
              fontSize: 34,
              fontWeight: FontWeight.bold,
              color: Colors.black,
              letterSpacing: 0.38,
            ),
          ),
          const SizedBox(height: 8),
          // Subtitle SF Pro Text Regular 17pt #6E6E73
          const Text(
            'Select a premium account card from your database to link as your active card.',
            style: TextStyle(
              fontFamily: 'SF Pro Text',
              fontSize: 17,
              fontWeight: FontWeight.normal,
              color: Color(0xFF6E6E73),
              letterSpacing: -0.41,
            ),
          ),
          const SizedBox(height: 24),
          
          Expanded(
            child: _loadingAccounts
                ? const Center(child: CupertinoActivityIndicator(color: Color(0xFF000000), radius: 14))
                : _error != null
                    ? Center(
                        child: Text(
                          'Error loading accounts: $_error',
                          style: const TextStyle(
                            fontFamily: 'SF Pro Text',
                            color: Color(0xFFFF3B30),
                          ),
                        ),
                      )
                    : _accounts.isEmpty
                        ? const Center(
                            child: Text(
                              'No accounts found in database.',
                              style: TextStyle(
                                fontFamily: 'SF Pro Text',
                                color: Color(0xFF6E6E73),
                                fontSize: 15,
                              ),
                            ),
                          )
                        : Container(
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: const Color(0xFFE5E5EA),
                                width: 0.5,
                              ),
                            ),
                            child: ListView.separated(
                              shrinkWrap: true,
                              physics: const BouncingScrollPhysics(),
                              itemCount: _accounts.length,
                              separatorBuilder: (context, index) => const Divider(
                                height: 0.5,
                                thickness: 0.5,
                                color: Color(0xFFE5E5EA),
                                indent: 64,
                              ),
                              itemBuilder: (context, index) {
                                final acc = _accounts[index];
                                final isSelected = _linkedAccount?.accountId == acc.accountId;
                                return _buildAccountRow(acc, isSelected);
                              },
                            ),
                          ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildAccountRow(Account acc, bool isSelected) {
    return GestureDetector(
      onTap: () => setState(() => _linkedAccount = acc),
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: 60,
        padding: const EdgeInsets.symmetric(horizontal: 16.0),
        child: Row(
          children: [
            // Leading initials avatar (#F2F2F7 bg + #000000 text)
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: const Color(0xFFF2F2F7), // secondary tinted-glass style
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Text(
                  _getInitials(acc.customerName),
                  style: const TextStyle(
                    fontFamily: 'SF Pro Rounded',
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF000000), // active monochrome black
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    acc.customerName,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: 'SF Pro Text',
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      color: Colors.black,
                      letterSpacing: -0.41,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    acc.accountId,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: 'SF Pro Text',
                      fontSize: 13,
                      fontWeight: FontWeight.normal,
                      color: Color(0xFF6E6E73),
                      letterSpacing: -0.08,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '₹${acc.balance.toInt()}',
                  style: const TextStyle(
                    fontFamily: 'SF Pro Text',
                    fontSize: 17,
                    fontWeight: FontWeight.normal,
                    color: Color(0xFF3C3C43),
                  ),
                ),
                const SizedBox(width: 8),
                // Selected state gets checkmark.circle.fill in pure black #000000, else chevron.right in #C7C7CC
                isSelected
                    ? const Icon(
                        CupertinoIcons.checkmark_circle_fill,
                        color: Color(0xFF000000),
                        size: 20,
                      )
                    : const Icon(
                        CupertinoIcons.chevron_right,
                        color: Color(0xFFC7C7CC),
                        size: 13,
                      ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _getInitials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || name.isEmpty) return 'AC';
    if (parts.length == 1) {
      return parts[0].substring(0, parts[0].length >= 2 ? 2 : 1).toUpperCase();
    }
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  Widget _sectionHeader(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6.0, left: 4.0),
      child: Text(
        text.toUpperCase(),
        style: const TextStyle(
          fontFamily: 'SF Pro Text',
          fontSize: 13,
          fontWeight: FontWeight.w500,
          color: Color(0xFF6E6E73),
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  Widget _buildNavigationFooter() {
    String nextLabel = 'Continue →';
    if (_currentPage == 2) {
      nextLabel = 'Finish Setup →';
    }

    bool isNextDisabled = _currentPage == 2 && _linkedAccount == null;

    return Container(
      color: Colors.white,
      padding: const EdgeInsets.only(bottom: 24.0, top: 8.0, left: 20.0, right: 20.0),
      child: _currentPage == 0
          ? SizedBox(
              width: double.infinity,
              height: 50,
              child: CupertinoButton(
                padding: EdgeInsets.zero,
                color: const Color(0xFF000000), // monochrome black filled background
                disabledColor: const Color(0xFFE5E5EA), // disabled Apple state #E5E5EA
                borderRadius: BorderRadius.circular(14),
                onPressed: () {
                  _pageController.nextPage(
                    duration: const Duration(milliseconds: 300),
                    curve: Curves.easeInOut,
                  );
                },
                child: const Text(
                  'Continue →',
                  style: TextStyle(
                    fontFamily: 'SF Pro Rounded',
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
              ),
            )
          : Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Back text button left-aligned in pure black #000000
                CupertinoButton(
                  padding: EdgeInsets.zero,
                  onPressed: () {
                    _pageController.previousPage(
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut,
                    );
                  },
                  child: const Text(
                    'Back',
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      fontSize: 17,
                      color: Color(0xFF000000), // active monochrome
                    ),
                  ),
                ),
                
                // Filled 'Continue →' pill button right-aligned
                SizedBox(
                  height: 38,
                  child: CupertinoButton(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    color: const Color(0xFF000000), // pure black primary
                    disabledColor: const Color(0xFFE5E5EA), // #E5E5EA disabled
                    borderRadius: BorderRadius.circular(19), // Stadium shape
                    onPressed: isNextDisabled
                        ? null
                        : () {
                            if (_currentPage < 2) {
                              _pageController.nextPage(
                                duration: const Duration(milliseconds: 300),
                                curve: Curves.easeInOut,
                              );
                            } else {
                              _saveProfile();
                            }
                          },
                    child: Text(
                      nextLabel,
                      style: TextStyle(
                        fontFamily: 'SF Pro Rounded',
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: isNextDisabled ? const Color(0xFF8E8E93) : Colors.white, // #8E8E93 text when disabled
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
