import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';
import '../widgets/graph_canvas.dart';

class GraphScreen extends StatefulWidget {
  const GraphScreen({super.key});

  @override
  State<GraphScreen> createState() => _GraphScreenState();
}

class _GraphScreenState extends State<GraphScreen> {
  List<GraphNode> _nodes = [];
  List<GraphEdge> _edges = [];
  bool _loading = true;
  String? _error;

  // Segmented Control tab: 0 = 'Network', 1 = 'Fraud Rings', 2 = 'Risk Map'
  int _activeSegment = 0;

  // Graph state
  GraphNode? _selectedNode;

  @override
  void initState() {
    super.initState();
    _loadGraph();
  }

  Future<void> _loadGraph() async {
    setState(() {
      _loading = true;
      _selectedNode = null;
    });
    try {
      final data = await ApiService().fetchGraphCommunity(1);
      final nodes = _parseNodes(data);
      final edges = _parseEdges(data);
      setState(() {
        _nodes = nodes;
        _edges = edges;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  List<GraphNode> _parseNodes(Map<String, dynamic> data) {
    final nodeList = data['nodes'] as List<dynamic>? ??
        data['accounts'] as List<dynamic>? ?? [];
    int idx = 0;
    return nodeList.map((n) {
      final m = n as Map<String, dynamic>;
      final id = m['id']?.toString() ?? m['account_id']?.toString() ?? 'N$idx';
      final risk = m['risk_level']?.toString() ?? m['risk_profile']?.toString() ?? 'LOW';
      return GraphNode(
        id: id,
        label: m['label']?.toString() ?? m['account_id']?.toString() ?? 'Node${idx++}',
        pagerank: (m['pagerank'] as num?)?.toDouble() ??
            (m['score'] as num?)?.toDouble() ?? 0.3,
        riskLevel: risk,
        position: Offset.zero,
      );
    }).toList();
  }

  List<GraphEdge> _parseEdges(Map<String, dynamic> data) {
    final edgeList = data['edges'] as List<dynamic>? ??
        data['relationships'] as List<dynamic>? ?? [];
    return edgeList.map((e) {
      final m = e as Map<String, dynamic>;
      final s = m['source']?.toString() ?? m['from']?.toString() ?? '';
      final t = m['target']?.toString() ?? m['to']?.toString() ?? '';
      final isSusp = (m['weight'] as num? ?? 1.0) > 1.5;
      return GraphEdge(
        sourceId: s,
        targetId: t,
        weight: (m['weight'] as num?)?.toDouble() ?? 1.0,
        isSuspicious: isSusp,
      );
    }).toList();
  }

  void _onNodeSelected(GraphNode node) {
    HapticFeedback.mediumImpact();
    setState(() {
      _selectedNode = node;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2F2F7),
      appBar: _buildCupertinoAppBar(),
      body: Column(
        children: [
          // Segmented Control
          Container(
            color: Colors.white,
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 12),
            child: SizedBox(
              width: double.infinity,
              child: CupertinoSlidingSegmentedControl<int>(
                groupValue: _activeSegment,
                backgroundColor: const Color(0xFFF2F2F7),
                thumbColor: Colors.white,
                children: const {
                  0: Padding(
                    padding: EdgeInsets.symmetric(vertical: 8.0),
                    child: Text('Network', style: TextStyle(fontFamily: 'SF Pro Text', fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                  1: Padding(
                    padding: EdgeInsets.symmetric(vertical: 8.0),
                    child: Text('Fraud Rings', style: TextStyle(fontFamily: 'SF Pro Text', fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                  2: Padding(
                    padding: EdgeInsets.symmetric(vertical: 8.0),
                    child: Text('Risk Map', style: TextStyle(fontFamily: 'SF Pro Text', fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                },
                onValueChanged: (val) {
                  if (val != null) {
                    setState(() => _activeSegment = val);
                    _loadGraph();
                  }
                },
              ),
            ),
          ),

          // Main Canvas
          Expanded(
            child: Stack(
              children: [
                Positioned.fill(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.04),
                            blurRadius: 10,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: _loading
                          ? const Center(child: CupertinoActivityIndicator(color: Color(0xFF000000), radius: 12)) // Monochrome activity spinner
                          : _error != null && _nodes.isEmpty
                              ? _buildErrorState()
                              : GraphCanvas(
                                  nodes: _nodes,
                                  edges: _edges,
                                  selectedNode: _selectedNode,
                                  onNodeTap: _onNodeSelected,
                                ),
                    ),
                  ),
                ),

                // Apple Maps style bottom sheet
                if (_selectedNode != null)
                  Positioned(
                    left: 0,
                    right: 0,
                    bottom: 0,
                    child: _buildMapsStyleSheet(),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildCupertinoAppBar() {
    return AppBar(
      backgroundColor: Colors.white,
      elevation: 0,
      scrolledUnderElevation: 0,
      automaticallyImplyLeading: false,
      titleSpacing: 20.0,
      title: const Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            'Transaction Graph',
            style: TextStyle(
              fontFamily: 'SF Pro Text',
              color: Colors.black,
              fontSize: 17,
              fontWeight: FontWeight.w600,
            ),
          ),
          SizedBox(width: 24),
        ],
      ),
      actions: [
        IconButton(
          icon: const Icon(CupertinoIcons.refresh, color: Color(0xFF000000)), // Monochrome black refresh icon
          onPressed: _loadGraph,
        ),
        const SizedBox(width: 8),
      ],
    );
  }

  Widget _buildMapsStyleSheet() {
    final node = _selectedNode!;
    
    Color badgeColor = const Color(0xFF000000); // safe nodes color -> Monochrome black v2
    String riskLabel = 'SAFE';
    if (node.riskLevel.toUpperCase().contains('HIGH') || node.riskLevel.toUpperCase().contains('MULE')) {
      badgeColor = const Color(0xFFFF3B30); // red #FF3B30
      riskLabel = 'FLAGGED MULE';
    } else if (node.riskLevel.toUpperCase().contains('MEDIUM') || node.riskLevel.toUpperCase().contains('SUSPICIOUS')) {
      badgeColor = const Color(0xFFFF9500); // amber #FF9500
      riskLabel = 'SUSPICIOUS';
    }

    return Container(
      height: 280,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(
            color: Color(0x1A000000),
            blurRadius: 16,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // drag handle
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFC7C7CC),
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      node.id,
                      style: const TextStyle(
                        fontFamily: 'SF Pro Text',
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: Colors.black,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: badgeColor.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: badgeColor.withOpacity(0.3), width: 0.5),
                    ),
                    child: Text(
                      riskLabel,
                      style: TextStyle(
                        fontFamily: 'SF Pro Rounded',
                        color: badgeColor,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: () => setState(() => _selectedNode = null),
                    child: Container(
                      padding: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(
                        color: Color(0xFFF2F2F7),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(CupertinoIcons.xmark, size: 14, color: Color(0xFF8E8E93)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Stats Grid
              Expanded(
                child: Row(
                  children: [
                    _buildStatGridCell(
                      value: node.pagerank.toStringAsFixed(3),
                      label: 'Pagerank',
                    ),
                    _buildVerticalDivider(),
                    _buildStatGridCell(
                      value: node.riskLevel.toUpperCase().contains('HIGH') ? '₹3.4L' : '₹18K',
                      label: 'Volume',
                    ),
                    _buildVerticalDivider(),
                    _buildStatGridCell(
                      value: node.riskLevel.toUpperCase().contains('HIGH') ? '8' : '0',
                      label: 'Risk Flags',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // 'Investigate' button (Pill shape, #000000 filled, 50pt height)
              SizedBox(
                height: 50,
                child: ElevatedButton(
                  onPressed: () => _triggerManualInvestigation(node.id),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF000000), // Monochrome black action
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(25),
                    ),
                  ),
                  child: const Text(
                    'Investigate',
                    style: TextStyle(
                      fontFamily: 'SF Pro Rounded',
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatGridCell({required String value, required String label}) {
    return Expanded(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            value,
            style: const TextStyle(
              fontFamily: 'SF Pro Display',
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: Colors.black,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(
              fontFamily: 'SF Pro Text',
              fontSize: 13,
              color: Color(0xFF6E6E73),
              fontWeight: FontWeight.normal,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVerticalDivider() {
    return Container(
      width: 0.5,
      height: 40,
      color: const Color(0xFFE5E5EA),
    );
  }

  void _triggerManualInvestigation(String accountId) {
    HapticFeedback.heavyImpact();
    showCupertinoDialog(
      context: context,
      builder: (context) => CupertinoAlertDialog(
        title: const Text('Garuda Investigation Launched'),
        content: Text(
          'A comprehensive transaction ledger analysis has been initialized for Account ID: $accountId. '
          'Our GraphSAGE deep learning models are tracing surrounding node relationships.',
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            child: const Text('OK'),
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(CupertinoIcons.exclamationmark_circle, color: Colors.redAccent, size: 40),
          const SizedBox(height: 12),
          Text(
            _error ?? 'Failed to load ring network data',
            style: const TextStyle(fontFamily: 'SF Pro Text', color: Color(0xFF8E8E93)),
          ),
          const SizedBox(height: 12),
          CupertinoButton(
            color: const Color(0xFF000000), // Monochrome black action
            onPressed: _loadGraph,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}
