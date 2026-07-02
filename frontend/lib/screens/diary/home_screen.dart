import 'package:flutter/material.dart';
import '../../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService api = ApiService.instance;

  List<dynamic> diaries = [];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    loadDiaries();
  }

  Future<void> loadDiaries() async {
    final response = await api.getDiaries();

    setState(() {
      diaries = response ?? [];
      loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Your Diary")),
      floatingActionButton: FloatingActionButton(
        child: const Icon(Icons.add),
        onPressed: () => Navigator.pushNamed(context, "/write_diary"),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : diaries.isEmpty
              ? const Center(child: Text("No diary entries yet"))
              : ListView.builder(
                  itemCount: diaries.length,
                  itemBuilder: (context, index) {
                    final entry = diaries[index];
                    return Card(
                      child: ListTile(
                        title: Text(entry["content"] ?? ""),
                        subtitle: Text(entry["created_at"] ?? ""),
                      ),
                    );
                  },
                ),
    );
  }
}
