import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';

class GraphNode {
  final String id;
  final String label;
  final double pagerank;
  final String riskLevel; // "HIGH", "MEDIUM", "LOW"
  Offset position;
  Offset velocity;

  GraphNode({
    required this.id,
    required this.label,
    required this.pagerank,
    required this.riskLevel,
    required this.position,
    this.velocity = Offset.zero,
  });

  Color get color {
    switch (riskLevel.toUpperCase()) {
      case 'HIGH':
      case 'MULE':
        return const Color(0xFFFF3B30); // red #FF3B30
      case 'MEDIUM':
      case 'SUSPICIOUS':
        return const Color(0xFFFF9500); // amber #FF9500
      default:
        return const Color(0xFF000000); // monochrome safe black #000000
    }
  }

  String get initials {
    if (id.contains('GOLD')) return 'GD';
    if (id.contains('PLAT')) return 'PL';
    if (id.contains('EME') || id.contains('SENT')) return 'PE';
    final clean = label.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '');
    if (clean.length >= 2) return clean.substring(0, 2).toUpperCase();
    return id.substring(0, min(2, id.length)).toUpperCase();
  }
}

class GraphEdge {
  final String sourceId;
  final String targetId;
  final double weight;
  final bool isSuspicious;

  GraphEdge({
    required this.sourceId,
    required this.targetId,
    this.weight = 1.0,
    this.isSuspicious = false,
  });
}

class GraphCanvas extends StatefulWidget {
  final List<GraphNode> nodes;
  final List<GraphEdge> edges;
  final GraphNode? selectedNode;
  final Function(GraphNode)? onNodeTap;

  const GraphCanvas({
    super.key,
    required this.nodes,
    required this.edges,
    this.selectedNode,
    this.onNodeTap,
  });

  @override
  State<GraphCanvas> createState() => _GraphCanvasState();
}

class _GraphCanvasState extends State<GraphCanvas>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  double _scale = 1.0;
  Offset _offset = Offset.zero;
  Offset _panStart = Offset.zero;
  Offset _offsetStart = Offset.zero;
  final _random = Random();

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 16),
    )..addListener(_simulateForces);
    _controller.repeat();
    _initPositions();
  }

  void _initPositions() {
    for (final node in widget.nodes) {
      if (node.position == Offset.zero) {
        node.position = Offset(
          _random.nextDouble() * 260 - 130,
          _random.nextDouble() * 260 - 130,
        );
      }
    }
  }

  void _simulateForces() {
    if (!mounted) return;
    final nodes = widget.nodes;
    final edges = widget.edges;

    const repulsion = 4500.0;
    const attraction = 0.08;
    const damping = 0.82;

    for (final n in nodes) {
      Offset force = Offset.zero;

      // Repulsion
      for (final m in nodes) {
        if (m.id == n.id) continue;
        final delta = n.position - m.position;
        final dist = delta.distance.clamp(1.0, double.infinity);
        if (dist < 280) {
          force += delta / dist * (repulsion / (dist * dist));
        }
      }

      // Attraction along edges
      for (final e in edges) {
        GraphNode? other;
        if (e.sourceId == n.id) {
          other = nodes.firstWhere((x) => x.id == e.targetId,
              orElse: () => nodes.first);
        } else if (e.targetId == n.id) {
          other = nodes.firstWhere((x) => x.id == e.sourceId,
              orElse: () => nodes.first);
        }
        if (other != null) {
          final delta = other.position - n.position;
          force += delta * attraction;
        }
      }

      n.velocity = (n.velocity + force * 0.016) * damping;
      n.position += n.velocity;
    }

    setState(() {});
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onTapDown(TapDownDetails details) {
    // Convert click point back to local canvas space
    final RenderBox renderBox = context.findRenderObject() as RenderBox;
    final center = Offset(renderBox.size.width / 2, renderBox.size.height / 2);
    final localPos = (details.localPosition - _offset - center) / _scale;

    for (final node in widget.nodes) {
      final double radius = (widget.selectedNode?.id == node.id) ? 24.0 : 16.0;
      if ((localPos - node.position).distance <= radius + 15) {
        widget.onNodeTap?.call(node);
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: _onTapDown,
      onScaleStart: (details) {
        _panStart = details.focalPoint;
        _offsetStart = _offset;
      },
      onScaleUpdate: (details) {
        setState(() {
          _scale = (_scale * details.scale).clamp(0.4, 4.0);
          _offset = _offsetStart + (details.focalPoint - _panStart);
        });
      },
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: CustomPaint(
          painter: _GraphPainter(
            nodes: widget.nodes,
            edges: widget.edges,
            scale: _scale,
            offset: _offset,
            selectedNode: widget.selectedNode,
          ),
          child: Container(),
        ),
      ),
    );
  }
}

class _GraphPainter extends CustomPainter {
  final List<GraphNode> nodes;
  final List<GraphEdge> edges;
  final double scale;
  final Offset offset;
  final GraphNode? selectedNode;

  _GraphPainter({
    required this.nodes,
    required this.edges,
    required this.scale,
    required this.offset,
    this.selectedNode,
  });

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.translate(offset.dx + size.width / 2, offset.dy + size.height / 2);
    canvas.scale(scale);

    // 1. Draw Edges as 2pt lines
    for (final e in edges) {
      final source = nodes.firstWhere((n) => n.id == e.sourceId, orElse: () => nodes.first);
      final target = nodes.firstWhere((n) => n.id == e.targetId, orElse: () => nodes.last);

      final Color edgeColor = e.isSuspicious
          ? const Color(0x80FF9500) // #FF950080 (suspicious)
          : const Color(0x40000000); // #00000040 (monochrome safe)

      final edgePaint = Paint()
        ..color = edgeColor
        ..strokeWidth = 2.0
        ..style = PaintingStyle.stroke;

      canvas.drawLine(source.position, target.position, edgePaint);
    }

    // 2. Draw Nodes
    for (final node in nodes) {
      final isSelected = selectedNode?.id == node.id;
      final double radius = isSelected ? 24.0 : 16.0;

      // Draw Selected white ring outer border
      if (isSelected) {
        final ringPaint = Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 3.0;
        
        final shadowPaint = Paint()
          ..color = Colors.black.withOpacity(0.15)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
        
        canvas.drawCircle(node.position, radius + 2, shadowPaint);
        canvas.drawCircle(node.position, radius + 2, ringPaint);
      }

      // Draw node circle fill
      final nodePaint = Paint()
        ..color = node.color
        ..style = PaintingStyle.fill;
      canvas.drawCircle(node.position, radius, nodePaint);

      // Render SF Pro Rounded Bold 10pt account initials inside circle
      final textPainter = TextPainter(
        text: TextSpan(
          text: node.initials,
          style: const TextStyle(
            fontFamily: 'SF Pro Rounded',
            color: Colors.white,
            fontSize: 10,
            fontWeight: FontWeight.bold,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        node.position - Offset(textPainter.width / 2, textPainter.height / 2),
      );

      // Render descriptive small text under circle
      final labelPainter = TextPainter(
        text: TextSpan(
          text: node.label.length > 8 ? '${node.label.substring(0, 6)}..' : node.label,
          style: TextStyle(
            fontFamily: 'SF Pro Text',
            color: isSelected ? Colors.black : const Color(0xFF8E8E93),
            fontSize: 9,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      labelPainter.layout();
      labelPainter.paint(
        canvas,
        node.position + Offset(-labelPainter.width / 2, radius + 4),
      );
    }

    canvas.restore();
  }

  @override
  bool shouldRepaint(_GraphPainter old) => true;
}
