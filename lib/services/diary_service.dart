import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';
import '../models/diary_entry.dart';

class DiaryService {
  static Future<List<DiaryEntry>> getEntries() async {
    final url = Uri.parse('${ApiService.baseUrl}/diary');
    final headers = await ApiService.getHeaders();
    final response = await http.get(url, headers: headers);
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => DiaryEntry.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load diary entries');
    }
  }

  static Future<DiaryEntry> createEntry(String content) async {
    final url = Uri.parse('${ApiService.baseUrl}/diary');
    final headers = await ApiService.getHeaders();
    final response = await http.post(url, headers: headers, body: jsonEncode({'content': content}));
    if (response.statusCode == 200 || response.statusCode == 201) {
      return DiaryEntry.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to create diary entry');
    }
  }
}
