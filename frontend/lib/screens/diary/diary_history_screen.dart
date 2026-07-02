import 'package:flutter/material.dart';
import '../../services/api_service.dart';

class DiaryHistoryScreen extends StatefulWidget {
  @override
  State<DiaryHistoryScreen> createState() => _DiaryHistoryScreenState();
}

class _DiaryHistoryScreenState extends State<DiaryHistoryScreen> {
  List diaries = [];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    loadHistory();
  }

  Future<void> loadHistory() async {
    final data = await ApiService.getDiary();
    setState(() {
      diaries = data;
      loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Your Diary History"),
        backgroundColor: Colors.deepPurple,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: loadHistory,
          ),
        ],
      ),
      body: loading
          ? Center(child: CircularProgressIndicator())
          : diaries.isEmpty
              ? Center(
                  child: Text(
                    "No diary entries found",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
                  ),
                )
              : ListView.builder(
                  padding: EdgeInsets.all(12),
                  itemCount: diaries.length,
                  itemBuilder: (context, index) {
                    final entry = diaries[index];

                    return Card(
                      elevation: 3,
                      margin: EdgeInsets.only(bottom: 12),
                      child: ListTile(
                        title: Text(
                          entry["content"],
                          style: TextStyle(fontSize: 16),
                        ),
                        subtitle: Text(
                          entry["created_at"],
                          style: TextStyle(fontSize: 13, color: Colors.grey[700]),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
