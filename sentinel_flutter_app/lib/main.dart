import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/onboarding_screen.dart';
import 'screens/history_screen.dart';
import 'screens/graph_screen.dart';
import 'screens/home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  GoogleFonts.config.allowRuntimeFetching = false; // use bundled font only
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark, // Light mode status bar icons
      systemNavigationBarColor: Colors.white,
      systemNavigationBarIconBrightness: Brightness.dark,
    ),
  );
  runApp(const BOIFraudApp());
}

class BOIFraudApp extends StatelessWidget {
  const BOIFraudApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Garuda Sentinel',
      debugShowCheckedModeBanner: false,
      theme: _buildTheme(),
      home: const OnboardingDecisionWidget(),
      routes: {
        '/home': (context) => const MainShell(),
      },
    );
  }

  ThemeData _buildTheme() {
    const fontFamily = 'SF Pro Text';
    return ThemeData.light().copyWith(
      colorScheme: const ColorScheme.light(
        primary: Color(0xFF000000), // Pure black monochrome tint
        secondary: Color(0xFF8E8E93),
        error: Color(0xFFFF3B30),
        surface: Color(0xFFFFFFFF),
        background: Color(0xFFFFFFFF),
      ),
      scaffoldBackgroundColor: const Color(0xFFFFFFFF),
      textTheme: ThemeData.light().textTheme.apply(
        fontFamily: fontFamily,
        bodyColor: Colors.black,
        displayColor: Colors.black,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: IconThemeData(color: Colors.black),
        titleTextStyle: TextStyle(
          fontFamily: 'SF Pro Display',
          color: Colors.black,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      cardTheme: const CardThemeData(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
          side: BorderSide(color: Color(0xFFE5E5EA), width: 0.5),
        ),
      ),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: Color(0xFF1C1C1E),
        contentTextStyle: TextStyle(color: Colors.white, fontFamily: fontFamily),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
      ),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  final _pages = const [
    HomeScreen(),
    HistoryScreen(),
    GraphScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: _buildTabBar(),
    );
  }

  Widget _buildTabBar() {
    const tabs = [
      _TabItem(icon: CupertinoIcons.arrow_right, label: 'Pay'),
      _TabItem(icon: CupertinoIcons.list_bullet, label: 'History'),
      _TabItem(icon: CupertinoIcons.graph_square, label: 'Graph'),
    ];

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white, // Tab bar background white
        border: Border(top: BorderSide(color: Color(0xFFE5E5EA), width: 0.5)), // 0.5px top border
      ),
      child: SafeArea(
        child: SizedBox(
          height: 49, // Exact 49pt iOS height spec
          child: Row(
            children: List.generate(tabs.length, (i) {
              final selected = i == _currentIndex;
              final color = selected
                  ? const Color(0xFF000000) // Active tab tint #000000 (Monochrome)
                  : const Color(0xFF8E8E93); // Inactive tab tint #8E8E93
              return Expanded(
                child: GestureDetector(
                  onTap: () {
                    HapticFeedback.selectionClick();
                    setState(() => _currentIndex = i);
                  },
                  behavior: HitTestBehavior.opaque,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(tabs[i].icon, color: color, size: 21),
                      const SizedBox(height: 3),
                      Text(
                        tabs[i].label,
                        style: TextStyle(
                          fontFamily: 'SF Pro Text',
                          color: color,
                          fontSize: 10,
                          fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}

class _TabItem {
  final IconData icon;
  final String label;
  const _TabItem({required this.icon, required this.label});
}

class OnboardingDecisionWidget extends StatefulWidget {
  const OnboardingDecisionWidget({super.key});

  @override
  State<OnboardingDecisionWidget> createState() => _OnboardingDecisionWidgetState();
}

class _OnboardingDecisionWidgetState extends State<OnboardingDecisionWidget> {
  bool _isLoading = true;
  bool _isRegistered = false;

  @override
  void initState() {
    super.initState();
    _checkRegistration();
  }

  Future<void> _checkRegistration() async {
    final prefs = await SharedPreferences.getInstance();
    final registered = prefs.getBool('user_registered') ?? false;
    setState(() {
      _isRegistered = registered;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Colors.white,
        body: Center(
          child: CupertinoActivityIndicator(
            color: Color(0xFF000000),
            radius: 14,
          ),
        ),
      );
    }
    return _isRegistered ? const MainShell() : const OnboardingScreen();
  }
}
