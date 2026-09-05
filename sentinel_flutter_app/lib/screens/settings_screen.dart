import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../config/api_config.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _hostController;
  String? _testResult;
  bool _testing = false;
  Color _testColor = const Color(0xFF000000); // Black for positive state

  @override
  void initState() {
    super.initState();
    _hostController = TextEditingController(text: ApiConfig.defaultHost);
    _loadSaved();
  }

  Future<void> _loadSaved() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('backend_ip') ?? ApiConfig.defaultHost;
    setState(() => _hostController.text = saved);
  }

  Future<void> _save() async {
    HapticFeedback.mediumImpact();
    await ApiConfig.setHost(_hostController.text.trim());
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Settings saved'),
          backgroundColor: Color(0xFF000000), // Monochrome black
        ),
      );
      Navigator.pop(context);
    }
  }

  Future<void> _testConnection() async {
    HapticFeedback.selectionClick();
    setState(() {
      _testing = true;
      _testResult = null;
    });
    final start = DateTime.now();
    try {
      await ApiConfig.setHost(_hostController.text.trim());
      final stats = await ApiService().fetchGraphStats();
      final ms = DateTime.now().difference(start).inMilliseconds;
      final nodeCount = stats['node_count'] ?? stats['nodes'] ?? '?';
      setState(() {
        _testResult = '✅ Connected — ${ms}ms latency — $nodeCount nodes';
        _testColor = const Color(0xFF000000); // Monochrome Black
        _testing = false;
      });
    } catch (e) {
      final ms = DateTime.now().difference(start).inMilliseconds;
      setState(() {
        _testResult = '❌ Connection failed (${ms}ms): ${e.toString().split(':').last.trim()}';
        _testColor = const Color(0xFFFF3B30); // Alert red
        _testing = false;
      });
    }
  }

  @override
  void dispose() {
    _hostController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2F2F7), // systemBackground F2F2F7
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        leading: IconButton(
          icon: const Icon(CupertinoIcons.left_chevron, color: Color(0xFF000000)),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'Settings',
          style: TextStyle(
            fontFamily: 'SF Pro Display',
            color: Colors.black,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionHeader('BACKEND CONFIGURATION'),
            const SizedBox(height: 8),

            // Textfield in a clean grouped inset white card
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: TextField(
                controller: _hostController,
                style: const TextStyle(
                  fontFamily: 'SF Pro Text',
                  color: Colors.black,
                  fontSize: 16,
                ),
                decoration: const InputDecoration(
                  hintText: '192.168.1.100:8000',
                  hintStyle: TextStyle(color: Color(0xFF8E8E93)),
                  labelText: 'Backend Connection Address',
                  labelStyle: TextStyle(color: Color(0xFF8E8E93), fontSize: 13),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  prefixIcon: Icon(CupertinoIcons.link, color: Color(0xFF000000), size: 20),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Connection Test feedback widget
            if (_testResult != null)
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 16),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: _testColor.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _testColor.withOpacity(0.3), width: 0.5),
                ),
                child: Text(
                  _testResult!,
                  style: TextStyle(
                    fontFamily: 'SF Pro Text',
                    color: _testColor,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),

            // Test button in secondary tinted-glass action style
            SizedBox(
              width: double.infinity,
              height: 50,
              child: CupertinoButton(
                padding: EdgeInsets.zero,
                color: const Color(0xFFFFFFFF), // Custom light card action button
                borderRadius: BorderRadius.circular(25),
                onPressed: _testing ? null : _testConnection,
                child: Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFFF2F2F7), // secondary action Apple tint
                    borderRadius: BorderRadius.circular(25),
                  ),
                  child: Center(
                    child: _testing
                        ? const CupertinoActivityIndicator(color: Color(0xFF000000))
                        : const Text(
                            'Test Connection',
                            style: TextStyle(
                              fontFamily: 'SF Pro Rounded',
                              color: Color(0xFF000000),
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                          ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),

            // Save button: pill shape #000000 background with #FFFFFF text label, 50pt height
            SizedBox(
              width: double.infinity,
              height: 50,
              child: CupertinoButton(
                padding: EdgeInsets.zero,
                color: const Color(0xFF000000), // Monochrome black action
                borderRadius: BorderRadius.circular(25),
                onPressed: _save,
                child: const Text(
                  'Save Settings',
                  style: TextStyle(
                    fontFamily: 'SF Pro Rounded',
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 32),

            _sectionHeader('APP INFO'),
            const SizedBox(height: 8),

            // App details inset card
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
              ),
              child: Column(
                children: [
                  _infoTile('Version', '1.0.0 — Hackathon Build'),
                  _divider(),
                  _infoTile('Platform', 'Android ARM64'),
                  _divider(),
                  _infoTile('Engine', '⚙️ COBOL CBS + GraphSAGE + XGBoost'),
                  _divider(),
                  _infoTile('Regulatory', 'FIU-IND Compliant SAR'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionHeader(String text) {
    return Padding(
      padding: const EdgeInsets.only(left: 4.0),
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

  Widget _infoTile(String label, String value) {
    return Container(
      height: 44, // minimum touch/row targets
      padding: const EdgeInsets.symmetric(horizontal: 16.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontFamily: 'SF Pro Text',
              color: Color(0xFF8E8E93),
              fontSize: 15,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontFamily: 'SF Pro Text',
              color: Colors.black,
              fontSize: 15,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _divider() {
    return const Divider(
      height: 0.5,
      thickness: 0.5,
      color: Color(0xFFE5E5EA),
      indent: 16,
    );
  }
}
