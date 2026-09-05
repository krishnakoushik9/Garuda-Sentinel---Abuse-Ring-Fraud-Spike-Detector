import 'package:flutter/material.dart';
import '../models/account.dart';
import 'risk_badge.dart';

class AccountCard extends StatefulWidget {
  final Account account;
  final bool isSelected;
  final VoidCallback onTap;
  final double width;
  final double height;

  const AccountCard({
    super.key,
    required this.account,
    this.isSelected = false,
    required this.onTap,
    this.width = 280,
    this.height = 160,
  });

  @override
  State<AccountCard> createState() => _AccountCardState();
}

class _AccountCardState extends State<AccountCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _shimmerController;
  late Animation<double> _shimmerAnim;

  @override
  void initState() {
    super.initState();
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();
    _shimmerAnim = Tween<double>(begin: -1.0, end: 2.0).animate(
      CurvedAnimation(parent: _shimmerController, curve: Curves.linear),
    );
  }

  @override
  void dispose() {
    _shimmerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final account = widget.account;
    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
        width: widget.width,
        height: widget.height,
        transform: widget.isSelected
            ? (Matrix4.identity()..scale(1.03))
            : Matrix4.identity(),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [account.cardGradientStart, account.cardGradientEnd],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: widget.isSelected
                ? account.riskBadgeColor.withOpacity(0.8)
                : account.riskBadgeColor.withOpacity(0.3),
            width: widget.isSelected ? 2 : 1,
          ),
          boxShadow: widget.isSelected
              ? [
                  BoxShadow(
                    color: account.riskBadgeColor.withOpacity(0.4),
                    blurRadius: 20,
                    spreadRadius: 2,
                  )
                ]
              : [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.5),
                    blurRadius: 10,
                  )
                ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: AnimatedBuilder(
            animation: _shimmerAnim,
            builder: (context, child) {
              return ShaderMask(
                shaderCallback: (rect) {
                  return LinearGradient(
                    begin: Alignment.centerLeft,
                    end: Alignment.centerRight,
                    colors: const [
                      Colors.transparent,
                      Color(0x15FFFFFF),
                      Colors.transparent,
                    ],
                    stops: [
                      (_shimmerAnim.value - 0.3).clamp(0.0, 1.0),
                      _shimmerAnim.value.clamp(0.0, 1.0),
                      (_shimmerAnim.value + 0.3).clamp(0.0, 1.0),
                    ],
                  ).createShader(rect);
                },
                blendMode: BlendMode.srcOver,
                child: child,
              );
            },
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        account.accountId,
                        style: const TextStyle(
                          fontFamily: 'monospace',
                          color: Colors.white70,
                          fontSize: 12,
                          letterSpacing: 1,
                        ),
                      ),
                      RiskBadge(account: account),
                    ],
                  ),
                  const Spacer(),
                  Text(
                    account.customerName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    account.formattedBalance,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(
                        Icons.account_balance,
                        color: Colors.white38,
                        size: 14,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'BOI • ${account.maskedAccountId}',
                        style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// Mini card (120px height) for pay screen
class MiniAccountCard extends StatelessWidget {
  final Account? account;
  final String label;

  const MiniAccountCard({super.key, this.account, required this.label});

  @override
  Widget build(BuildContext context) {
    if (account == null) {
      return Container(
        height: 80,
        decoration: BoxDecoration(
          color: const Color(0xFF2C2C2E),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white12),
        ),
        child: Center(
          child: Text(
            'Select $label',
            style: const TextStyle(color: Colors.white38, fontSize: 14),
          ),
        ),
      );
    }
    final acc = account!;
    return Container(
      height: 80,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [acc.cardGradientStart, acc.cardGradientEnd],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: acc.riskBadgeColor.withOpacity(0.5)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                      color: Colors.white38,
                      fontSize: 11,
                      fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(
                  acc.customerName,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w700),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  acc.accountId,
                  style: const TextStyle(
                      color: Colors.white54, fontSize: 11, fontFamily: 'monospace'),
                ),
              ],
            ),
            const Spacer(),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  acc.formattedBalance,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: acc.riskBadgeColor.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(50),
                  ),
                  child: Text(
                    acc.riskBadgeLabel,
                    style: TextStyle(
                        color: acc.riskBadgeColor,
                        fontSize: 9,
                        fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
