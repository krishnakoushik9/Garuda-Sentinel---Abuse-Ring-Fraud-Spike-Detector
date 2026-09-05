import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import '../models/transaction.dart';
import '../services/api_service.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Transaction> _transactions = [];
  bool _loading = true;
  String? _error;

  // Search & Filter State
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String _selectedFilter = 'All'; // 'All', 'Clean', 'Suspicious', 'Mule'

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadTransactions() async {
    setState(() => _loading = true);
    try {
      final txns = await ApiService().fetchTransactions(limit: 50);
      setState(() {
        _transactions = txns;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  List<Transaction> get _filteredTransactions {
    return _transactions.where((txn) {
      // 1. Search Query filter
      final matchesSearch = txn.senderId.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          txn.receiverId.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          txn.channel.toLowerCase().contains(_searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      // 2. Risk level filter
      if (_selectedFilter == 'Clean') {
        return txn.riskScore <= 0.4;
      } else if (_selectedFilter == 'Suspicious') {
        return txn.riskScore > 0.4 && txn.riskScore <= 0.7;
      } else if (_selectedFilter == 'Mule') {
        return txn.riskScore > 0.7;
      }

      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final filteredList = _filteredTransactions;

    // Split filtered list into "TODAY", "YESTERDAY" and "PAST ACTIVITY"
    final List<Transaction> todayTxns = [];
    final List<Transaction> yesterdayTxns = [];
    final List<Transaction> pastTxns = [];

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final yesterday = today.subtract(const Duration(days: 1));

    for (final txn in filteredList) {
      final dt = txn.parsedDateTime;
      final txnDate = DateTime(dt.year, dt.month, dt.day);
      if (txnDate.isAtSameMomentAs(today)) {
        todayTxns.add(txn);
      } else if (txnDate.isAtSameMomentAs(yesterday)) {
        yesterdayTxns.add(txn);
      } else {
        pastTxns.add(txn);
      }
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF2F2F7), // systemGroupedBackground F2F2F7
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        automaticallyImplyLeading: false,
        titleSpacing: 20.0,
        title: const Text(
          'Transactions',
          style: TextStyle(
            fontFamily: 'SF Pro Display',
            color: Colors.black,
            fontSize: 20,
            fontWeight: FontWeight.w600,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(CupertinoIcons.arrow_2_circlepath, color: Color(0xFF000000)), // Monochrome Black refresh
            onPressed: _loadTransactions,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _loading
          ? const Center(child: CupertinoActivityIndicator(color: Color(0xFF000000), radius: 12))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Top White Section for Title, Search & Filter Chips
                Container(
                  color: Colors.white,
                  padding: const EdgeInsets.only(left: 20.0, right: 20.0, bottom: 16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Large title 'History' SF Pro Display Bold 34pt
                      const Text(
                        'History',
                        style: TextStyle(
                          fontFamily: 'SF Pro Display',
                          fontSize: 34,
                          fontWeight: FontWeight.bold,
                          color: Colors.black,
                        ),
                      ),
                      const SizedBox(height: 12),

                      // Search bar
                      Container(
                        height: 38,
                        decoration: BoxDecoration(
                          color: const Color(0xFFF2F2F7),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: TextField(
                          controller: _searchController,
                          onChanged: (val) {
                            setState(() {
                              _searchQuery = val;
                            });
                          },
                          style: const TextStyle(
                            fontFamily: 'SF Pro Text',
                            color: Colors.black,
                            fontSize: 15,
                          ),
                          decoration: const InputDecoration(
                            hintText: 'Search transactions',
                            hintStyle: TextStyle(
                              fontFamily: 'SF Pro Text',
                              color: Color(0xFF8E8E93),
                              fontSize: 15,
                            ),
                            prefixIcon: Icon(
                              CupertinoIcons.search,
                              color: Color(0xFF8E8E93),
                              size: 18,
                            ),
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(vertical: 9.0),
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Filter chips horizontal scroll
                      _buildFilterChips(),
                    ],
                  ),
                ),

                // Inset Grouped List body
                Expanded(
                  child: filteredList.isEmpty
                      ? _buildEmptyState()
                      : ListView(
                          physics: const BouncingScrollPhysics(),
                          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
                          children: [
                            if (todayTxns.isNotEmpty) ...[
                              _buildDateSectionHeader('TODAY'),
                              _buildGroupedCardContainer(todayTxns),
                              const SizedBox(height: 20),
                            ],
                            if (yesterdayTxns.isNotEmpty) ...[
                              _buildDateSectionHeader('YESTERDAY'),
                              _buildGroupedCardContainer(yesterdayTxns),
                              const SizedBox(height: 20),
                            ],
                            if (pastTxns.isNotEmpty) ...[
                              _buildDateSectionHeader('PAST ACTIVITY'),
                              _buildGroupedCardContainer(pastTxns),
                              const SizedBox(height: 24),
                            ],
                          ],
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildFilterChips() {
    final chips = ['All', 'Clean', 'Suspicious', 'Mule'];
    return SizedBox(
      height: 32,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final isSelected = _selectedFilter == chips[i];
          return GestureDetector(
            onTap: () {
              HapticFeedback.selectionClick();
              setState(() {
                _selectedFilter = chips[i];
              });
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              decoration: BoxDecoration(
                color: isSelected ? const Color(0xFF000000) : const Color(0xFFF2F2F7), // #000000 monochrome active chip
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: Text(
                  chips[i],
                  style: TextStyle(
                    fontFamily: 'SF Pro Text',
                    color: isSelected ? Colors.white : const Color(0xFF3C3C43),
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildDateSectionHeader(String title) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // date section headers SF Pro Text Medium 13pt #6E6E73
        Text(
          title,
          style: const TextStyle(
            fontFamily: 'SF Pro Text',
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: Color(0xFF6E6E73),
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 4),
        const Divider(color: Color(0xFFE5E5EA), height: 1, thickness: 0.5),
        const SizedBox(height: 8),
      ],
    );
  }

  Widget _buildGroupedCardContainer(List<Transaction> transactions) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        padding: EdgeInsets.zero,
        itemCount: transactions.length,
        separatorBuilder: (_, __) => const Divider(
          color: Color(0xFFE5E5EA),
          height: 1,
          thickness: 0.5,
          indent: 64,
        ),
        itemBuilder: (context, i) {
          return _buildTxnRow(transactions[i]);
        },
      ),
    );
  }

  Widget _buildTxnRow(Transaction txn) {
    Color riskDotColor = const Color(0xFF000000); // Monochrome default
    if (txn.riskScore > 0.7) {
      riskDotColor = const Color(0xFFFF3B30); // Red
    } else if (txn.riskScore > 0.4) {
      riskDotColor = const Color(0xFFFF9500); // Amber v2
    }

    final isCredit = txn.receiverId.toLowerCase().contains('boi') || 
        txn.receiverId.toLowerCase().contains('self') ||
        txn.formattedAmount.contains('+');

    return GestureDetector(
      onTap: () => _showDetailSheet(txn),
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: 60,
        padding: const EdgeInsets.symmetric(horizontal: 14.0),
        child: Row(
          children: [
            // leading initials avatar (#F2F2F7 bg + #000000 text)
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: const Color(0xFFF2F2F7),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Text(
                  _getInitials(txn.receiverId),
                  style: const TextStyle(
                    fontFamily: 'SF Pro Rounded',
                    color: Color(0xFF000000), // active monochrome
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          txn.receiverId.split('_').first.toUpperCase(),
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: Colors.black,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      // channel badge inline pill (#F2F2F7 bg + #000000 text)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF2F2F7), // v2 Monochrome style
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          txn.channel,
                          style: const TextStyle(
                            fontFamily: 'SF Pro Text',
                            fontSize: 9,
                            fontWeight: FontWeight.w500,
                            color: Color(0xFF000000),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    txn.formattedTime,
                    style: const TextStyle(
                      fontFamily: 'SF Pro Text',
                      fontSize: 12,
                      color: Color(0xFF8E8E93),
                    ),
                  ),
                ],
              ),
            ),
            // amount right-aligned (#000000 credit, #FF3B30 debit)
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  txn.formattedAmount,
                  style: TextStyle(
                    fontFamily: 'SF Pro Text',
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: isCredit ? const Color(0xFF000000) : const Color(0xFFFF3B30),
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: riskDotColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${(txn.riskScore * 100).toStringAsFixed(0)}% Risk',
                      style: TextStyle(
                        fontFamily: 'SF Pro Text',
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: riskDotColor,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showDetailSheet(Transaction txn) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _TxnDetailSheet(txn: txn),
    );
  }

  String _getInitials(String text) {
    final clean = text.replaceAll(RegExp(r'[^a-zA-Z\s]'), '').trim();
    if (clean.isEmpty) return 'TX';
    final parts = clean.split(RegExp(r'\s+'));
    if (parts.length == 1) {
      return parts[0].substring(0, parts[0].length >= 2 ? 2 : 1).toUpperCase();
    }
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(CupertinoIcons.square_list, color: Color(0xFF8E8E93), size: 48),
          const SizedBox(height: 12),
          const Text(
            'No matching transactions found',
            style: TextStyle(
              fontFamily: 'SF Pro Text',
              color: Color(0xFF8E8E93),
              fontSize: 15,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(
              _error!,
              style: const TextStyle(color: Colors.redAccent, fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ]
        ],
      ),
    );
  }
}

class _TxnDetailSheet extends StatelessWidget {
  final Transaction txn;
  const _TxnDetailSheet({required this.txn});

  @override
  Widget build(BuildContext context) {
    Color riskColor = const Color(0xFF000000); // Monochrome Black
    String riskVerdict = 'CLEAN';
    if (txn.riskScore > 0.7) {
      riskColor = const Color(0xFFFF3B30); // Red
      riskVerdict = 'SUSPICIOUS / MULE HIGH';
    } else if (txn.riskScore > 0.4) {
      riskColor = const Color(0xFFFF9500); // Amber v2
      riskVerdict = 'ELEVATED RISK';
    }

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Top drag handle
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
            const SizedBox(height: 20),

            // Large visual amount
            Center(
              child: Text(
                txn.formattedAmount,
                style: const TextStyle(
                  fontFamily: 'SF Pro Display',
                  color: Colors.black,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Details rows
            _detailRow('Transaction ID', txn.transactionId),
            _detailRow('Sender Account', txn.senderId),
            _detailRow('Receiver Account', txn.receiverId),
            _detailRow('Channel Method', txn.channel),
            _detailRow('Timestamp', txn.timestamp),
            
            // Risk detailed status
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Fraud Risk Score',
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      color: Color(0xFF6E6E73),
                      fontSize: 14,
                    ),
                  ),
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: riskColor,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '${(txn.riskScore * 100).toStringAsFixed(1)}% ($riskVerdict)',
                        style: TextStyle(
                          fontFamily: 'SF Pro Text',
                          color: riskColor,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontFamily: 'SF Pro Text',
              color: Color(0xFF6E6E73),
              fontSize: 14,
            ),
          ),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontFamily: 'SF Pro Text',
                color: Colors.black,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
