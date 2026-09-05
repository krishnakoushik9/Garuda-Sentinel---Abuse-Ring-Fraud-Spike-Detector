import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/investigation.dart';

// ─── Confetti Particle ───────────────────────────────────────────────────────
class _ConfettiParticle {
  double x, y, vx, vy, size, rotation, rotationSpeed;
  Color color;

  _ConfettiParticle({
    required this.x,
    required this.y,
    required this.vx,
    required this.vy,
    required this.size,
    required this.rotation,
    required this.rotationSpeed,
    required this.color,
  });
}

class _ConfettiPainter extends CustomPainter {
  final List<_ConfettiParticle> particles;
  _ConfettiPainter(this.particles);

  @override
  void paint(Canvas canvas, Size size) {
    for (final p in particles) {
      final paint = Paint()..color = p.color;
      canvas.save();
      canvas.translate(p.x, p.y);
      canvas.rotate(p.rotation);
      canvas.drawRect(
          Rect.fromCenter(center: Offset.zero, width: p.size, height: p.size * 0.5),
          paint);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter old) => true;
}

// ─── Checkmark Painter ───────────────────────────────────────────────────────
class _CheckmarkPainter extends CustomPainter {
  final double progress;
  final Color color;
  _CheckmarkPainter(this.progress, this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final path = Path();
    path.moveTo(size.width * 0.2, size.height * 0.5);
    path.lineTo(size.width * 0.42, size.height * 0.72);
    path.lineTo(size.width * 0.78, size.height * 0.28);

    final pathMetrics = path.computeMetrics().first;
    final extractedPath =
        pathMetrics.extractPath(0, pathMetrics.length * progress);
    canvas.drawPath(extractedPath, paint);
  }

  @override
  bool shouldRepaint(_CheckmarkPainter old) => old.progress != progress;
}

// ─── Result Modal ─────────────────────────────────────────────────────────────
void showResultModal({
  required BuildContext context,
  required Investigation investigation,
  bool isMuleSimulation = false,
  String? txnAmount,
  String? txnId,
  VoidCallback? onViewSAR,
}) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _ResultModal(
      investigation: investigation,
      isMuleSimulation: isMuleSimulation,
      txnAmount: txnAmount,
      txnId: txnId,
      onViewSAR: onViewSAR,
    ),
  );
}

class _ResultModal extends StatefulWidget {
  final Investigation investigation;
  final bool isMuleSimulation;
  final String? txnAmount;
  final String? txnId;
  final VoidCallback? onViewSAR;

  const _ResultModal({
    required this.investigation,
    this.isMuleSimulation = false,
    this.txnAmount,
    this.txnId,
    this.onViewSAR,
  });

  @override
  State<_ResultModal> createState() => _ResultModalState();
}

class _ResultModalState extends State<_ResultModal>
    with TickerProviderStateMixin {
  late AnimationController _iconController;
  late AnimationController _confettiController;
  late List<_ConfettiParticle> _particles;
  bool _showFullNarrative = false;
  final _random = Random();

  @override
  void initState() {
    super.initState();
    _iconController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _confettiController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    );

    _particles = _generateParticles();
    _iconController.forward();

    if (widget.investigation.isClean) {
      _confettiController.forward();
    }
  }

  List<_ConfettiParticle> _generateParticles() {
    // Beautiful monochrome confetti palette
    final colors = [
      const Color(0xFF000000), // pure black
      const Color(0xFF8E8E93), // iOS grey
      const Color(0xFFD1D1D6), // light grey
      const Color(0xFF3A3A3C), // dark grey
      const Color(0xFFE5E5EA), // silver
    ];
    return List.generate(20, (i) {
      return _ConfettiParticle(
        x: 150 + _random.nextDouble() * 100,
        y: -20,
        vx: (_random.nextDouble() - 0.5) * 6,
        vy: _random.nextDouble() * 4 + 2,
        size: _random.nextDouble() * 10 + 5,
        rotation: _random.nextDouble() * pi * 2,
        rotationSpeed: (_random.nextDouble() - 0.5) * 0.2,
        color: colors[_random.nextInt(colors.length)],
      );
    });
  }

  @override
  void dispose() {
    _iconController.dispose();
    _confettiController.dispose();
    super.dispose();
  }

  Color get _modalColor => Colors.white; // systemBackground #FFFFFF

  Color get _accentColor {
    if (widget.investigation.isFraud) return const Color(0xFFFF3B30); // Destructive/alert red
    if (widget.investigation.isClean) return const Color(0xFF000000); // Monochrome black
    return const Color(0xFFFF9500); // Amber warning
  }

  @override
  Widget build(BuildContext context) {
    final inv = widget.investigation;

    return AnimatedBuilder(
      animation: _confettiController,
      builder: (context, child) {
        if (inv.isClean && _confettiController.isAnimating) {
          for (final p in _particles) {
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.15; // gravity
            p.rotation += p.rotationSpeed;
          }
        }

        return Stack(
          children: [
            if (inv.isClean)
              Positioned.fill(
                child: IgnorePointer(
                  child: CustomPaint(
                    painter: _ConfettiPainter(_particles),
                  ),
                ),
              ),
            child!,
          ],
        );
      },
      child: DraggableScrollableSheet(
        initialChildSize: 0.7,
        minChildSize: 0.5,
        maxChildSize: 0.92,
        builder: (_, controller) {
          return Container(
            decoration: BoxDecoration(
              color: _modalColor,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.08),
                  blurRadius: 16,
                  offset: const Offset(0, -4),
                )
              ],
            ),
            child: ListView(
              controller: controller,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              children: [
                // Apple Maps style drag handle
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    decoration: BoxDecoration(
                      color: const Color(0xFFC7C7CC),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Icon
                Center(child: _buildIcon()),
                const SizedBox(height: 20),

                // COBOL badge (only on fraud)
                if (inv.isFraud)
                  Center(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF2F2F7), // secondary action Apple tint background
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFFF9500), width: 0.5),
                      ),
                      child: const Text(
                        '⚙️ COBOL CBS INTERCEPTED',
                        style: TextStyle(
                          fontFamily: 'SF Pro Rounded',
                          color: Color(0xFFFF9500),
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ),

                // Title in SF Pro Display Bold
                Center(
                  child: Text(
                    _getTitle(),
                    style: const TextStyle(
                      fontFamily: 'SF Pro Display',
                      color: Colors.black,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      letterSpacing: -0.3,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 12),

                // Risk score / amount badge
                Center(child: _buildBadge()),
                const SizedBox(height: 20),

                // Mule simulation warning banner
                if (widget.isMuleSimulation && inv.isFraud)
                  Container(
                    padding: const EdgeInsets.all(14),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF3B30).withOpacity(0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFFF3B30).withOpacity(0.3), width: 0.5),
                    ),
                    child: const Text(
                      'STRUCTURING DETECTED — Amount ₹9,900 matches known smurfing pattern (below ₹10,000 PAN threshold)',
                      style: TextStyle(
                        fontFamily: 'SF Pro Text',
                        color: Color(0xFFFF3B30),
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        height: 1.3,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),

                // Narrative
                if (inv.explanationNarrative.isNotEmpty)
                  _buildNarrative(),

                // Txn ID details section inside a white UITableView card
                if (inv.isClean && widget.txnId != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFFF2F2F7),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    child: Column(
                      children: [
                        _infoRow('Transaction ID', widget.txnId!),
                        const Divider(color: Color(0xFFE5E5EA), height: 16, thickness: 0.5),
                        if (widget.txnAmount != null)
                          _infoRow('Settle Amount', '₹${widget.txnAmount}'),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 28),
                _buildButtons(context),
                const SizedBox(height: 16),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildIcon() {
    if (widget.investigation.isFraud) {
      return ScaleTransition(
        scale: CurvedAnimation(
          parent: _iconController,
          curve: Curves.elasticOut,
        ),
        child: Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: const Color(0xFFFF3B30).withOpacity(0.08),
            shape: BoxShape.circle,
            border: Border.all(color: const Color(0xFFFF3B30), width: 2),
          ),
          child: const Center(
            child: Text('❌', style: TextStyle(fontSize: 36)),
          ),
        ),
      );
    }
    if (widget.investigation.isClean) {
      return AnimatedBuilder(
        animation: _iconController,
        builder: (_, __) => Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: const Color(0xFFF2F2F7), // secondary tinted-glass style
            shape: BoxShape.circle,
            border: Border.all(color: const Color(0xFF000000), width: 2),
          ),
          child: CustomPaint(
            painter: _CheckmarkPainter(
                _iconController.value, const Color(0xFF000000)), // Monochrome Black checkmark
          ),
        ),
      );
    }
    // Warning
    return BounceAnimation(
      child: Container(
        width: 80,
        height: 80,
        decoration: BoxDecoration(
          color: const Color(0xFFFF9500).withOpacity(0.08),
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFFFF9500), width: 2),
        ),
        child:
            const Center(child: Text('⚠️', style: TextStyle(fontSize: 36))),
      ),
    );
  }

  String _getTitle() {
    if (widget.investigation.isFraud) return 'Transaction BLOCKED';
    if (widget.investigation.isClean) return 'Payment Successful';
    return 'Transaction Flagged';
  }

  Widget _buildBadge() {
    final inv = widget.investigation;
    if (inv.isFraud) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFFFF3B30).withOpacity(0.08),
          borderRadius: BorderRadius.circular(50),
          border: Border.all(color: const Color(0xFFFF3B30), width: 0.5),
        ),
        child: Text(
          'RISK: ${inv.riskPercent}',
          style: const TextStyle(
            fontFamily: 'SF Pro Text',
            color: Color(0xFFFF3B30),
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
        ),
      );
    }
    if (inv.isClean) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFFF2F2F7),
          borderRadius: BorderRadius.circular(50),
          border: Border.all(color: const Color(0xFF000000), width: 0.5),
        ),
        child: Text(
          widget.txnAmount != null ? 'Amount: ₹${widget.txnAmount}' : '✅ Approved',
          style: const TextStyle(
            fontFamily: 'SF Pro Text',
            color: Color(0xFF000000),
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFFF9500).withOpacity(0.08),
        borderRadius: BorderRadius.circular(50),
        border: Border.all(color: const Color(0xFFFF9500), width: 0.5),
      ),
      child: Text(
        'RISK: ${inv.riskPercent}',
        style: const TextStyle(
          fontFamily: 'SF Pro Text',
          color: Color(0xFFFF9500),
          fontWeight: FontWeight.bold,
          fontSize: 15,
        ),
      ),
    );
  }

  Widget _buildNarrative() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'RISK INTELLIGENCE REPORT',
          style: TextStyle(
            fontFamily: 'SF Pro Text',
            color: Color(0xFF8E8E93),
            fontSize: 12,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          widget.investigation.explanationNarrative,
          style: const TextStyle(
            fontFamily: 'SF Pro Text',
            color: Colors.black87,
            fontSize: 14,
            height: 1.4,
          ),
          maxLines: _showFullNarrative ? null : 3,
          overflow: _showFullNarrative ? null : TextOverflow.ellipsis,
        ),
        if (!_showFullNarrative &&
            widget.investigation.explanationNarrative.length > 120)
          GestureDetector(
            onTap: () => setState(() => _showFullNarrative = true),
            child: const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'Show Full Report ▼',
                style: TextStyle(
                  fontFamily: 'SF Pro Text',
                  color: Color(0xFF000000),
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _infoRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontFamily: 'SF Pro Text',
            color: Color(0xFF8E8E93),
            fontSize: 13,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontFamily: 'SF Pro Text',
            color: Colors.black,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildButtons(BuildContext context) {
    final inv = widget.investigation;
    if (inv.isFraud) {
      return Row(
        children: [
          Expanded(
            child: _OutlineButton(
              label: 'Dismiss',
              color: const Color(0xFFFF3B30),
              onTap: () => Navigator.pop(context),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _FilledButton(
              label: 'View SAR Report',
              color: const Color(0xFFFF3B30),
              onTap: () {
                Navigator.pop(context);
                widget.onViewSAR?.call();
              },
            ),
          ),
        ],
      );
    }
    if (inv.isClean) {
      return _FilledButton(
        label: 'Done',
        color: const Color(0xFF000000),
        onTap: () => Navigator.pop(context),
      );
    }
    // Suspicious
    return Row(
      children: [
        Expanded(
          child: _OutlineButton(
            label: 'Done',
            color: const Color(0xFF000000),
            onTap: () => Navigator.pop(context),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _FilledButton(
            label: 'Report Suspicious',
            color: const Color(0xFFFF9500),
            onTap: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Flagged for manual review'),
                  backgroundColor: Color(0xFF000000),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _FilledButton extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _FilledButton(
      {required this.label, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 50,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(14), // 14pt corner radius as spec
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.12),
              blurRadius: 8,
              offset: const Offset(0, 2),
            )
          ],
        ),
        child: Center(
          child: Text(
            label,
            style: const TextStyle(
              fontFamily: 'SF Pro Rounded',
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 15,
            ),
          ),
        ),
      ),
    );
  }
}

class _OutlineButton extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _OutlineButton(
      {required this.label, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 50,
        decoration: BoxDecoration(
          color: const Color(0xFFF2F2F7), // secondary tinted-glass style
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withOpacity(0.3), width: 0.5),
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              fontFamily: 'SF Pro Rounded',
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 15,
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Bounce Animation ─────────────────────────────────────────────────────────
class BounceAnimation extends StatefulWidget {
  final Widget child;
  const BounceAnimation({super.key, required this.child});

  @override
  State<BounceAnimation> createState() => _BounceAnimationState();
}

class _BounceAnimationState extends State<BounceAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, child) {
        return Transform.translate(
          offset: Offset(0, -6 * _controller.value),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}
