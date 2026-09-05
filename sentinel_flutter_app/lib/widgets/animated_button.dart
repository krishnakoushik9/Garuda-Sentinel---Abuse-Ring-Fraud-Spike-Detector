import 'dart:async';
import 'package:flutter/material.dart';

enum ButtonState { idle, loading }

class AnimatedSendButton extends StatefulWidget {
  final ButtonState state;
  final String idleLabel;
  final VoidCallback? onPressed;

  const AnimatedSendButton({
    super.key,
    required this.state,
    required this.idleLabel,
    this.onPressed,
  });

  @override
  State<AnimatedSendButton> createState() => _AnimatedSendButtonState();
}

class _AnimatedSendButtonState extends State<AnimatedSendButton>
    with TickerProviderStateMixin {
  late AnimationController _shimmerController;
  late Animation<double> _shimmerAnim;

  Timer? _textTimer;
  int _textIndex = 0;
  final List<String> _loadingTexts = [
    'Processing...',
    'Analyzing...',
    'Checking Risk...',
    'Verifying...',
  ];

  @override
  void initState() {
    super.initState();
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
    _shimmerAnim = Tween<double>(begin: -1.0, end: 2.0).animate(
      CurvedAnimation(parent: _shimmerController, curve: Curves.linear),
    );
  }

  @override
  void didUpdateWidget(AnimatedSendButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.state == ButtonState.loading &&
        oldWidget.state != ButtonState.loading) {
      _startTextCycle();
    } else if (widget.state != ButtonState.loading) {
      _stopTextCycle();
    }
  }

  void _startTextCycle() {
    _textIndex = 0;
    _textTimer = Timer.periodic(const Duration(milliseconds: 600), (_) {
      if (mounted) {
        setState(() {
          _textIndex = (_textIndex + 1) % _loadingTexts.length;
        });
      }
    });
  }

  void _stopTextCycle() {
    _textTimer?.cancel();
    _textTimer = null;
  }

  @override
  void dispose() {
    _shimmerController.dispose();
    _textTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = widget.state == ButtonState.loading;

    return GestureDetector(
      onTap: isLoading ? null : widget.onPressed,
      child: AnimatedBuilder(
        animation: _shimmerAnim,
        builder: (context, child) {
          return Container(
            height: 50, // exact 50pt height
            decoration: BoxDecoration(
              color: const Color(0xFF000000), // pure black primary
              gradient: isLoading
                  ? LinearGradient(
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                      colors: const [
                        Color(0xFF1C1C1E),
                        Color(0xFF3A3A3C),
                        Color(0xFF1C1C1E),
                      ],
                      stops: [
                        (_shimmerAnim.value - 0.5).clamp(0.0, 1.0),
                        _shimmerAnim.value.clamp(0.0, 1.0),
                        (_shimmerAnim.value + 0.5).clamp(0.0, 1.0),
                      ],
                    )
                  : null,
              borderRadius: BorderRadius.circular(14), // 14pt corner radius as spec
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.08), // Apple standard shadow
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Center(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                transitionBuilder: (child, anim) {
                  return FadeTransition(
                    opacity: anim,
                    child: SlideTransition(
                      position: Tween<Offset>(
                        begin: const Offset(0, 0.2),
                        end: Offset.zero,
                      ).animate(anim),
                      child: child,
                    ),
                  );
                },
                child: isLoading
                    ? Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            _loadingTexts[_textIndex],
                            key: ValueKey(_textIndex),
                            style: const TextStyle(
                              fontFamily: 'SF Pro Rounded',
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      )
                    : Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.currency_rupee,
                              color: Colors.white, size: 18),
                          const SizedBox(width: 4),
                          Text(
                            widget.idleLabel,
                            key: const ValueKey('idle'),
                            style: const TextStyle(
                              fontFamily: 'SF Pro Rounded',
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                              letterSpacing: -0.2,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
          );
        },
      ),
    );
  }
}
