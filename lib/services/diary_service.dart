import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';
import '../models/diary_entry.dart';

class DiaryService {
  static Future<List<DiaryEntry>> getEntries() async {
    final url = Uri.parse('${ApiService.baseUrl}/diary');
    final headers = await ApiService.getHeaders();
    final response = await http.get(url, headers: headers);
    await ApiService.ensureSuccess(response, 'Could not load diary entries.');
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => DiaryEntry.fromJson(json)).toList();
    }
    throw Exception('The diary API returned an unexpected response.');
  }

  static Future<DiaryEntry> createEntry(
    String content, {
    String? title,
    String? mood,
  }) async {
    final url = Uri.parse('${ApiService.baseUrl}/diary');
    final headers = await ApiService.getHeaders();
    final response = await http.post(
      url,
      headers: headers,
      body: jsonEncode({'content': content, 'title': title, 'mood': mood}),
    );
    await ApiService.ensureSuccess(response, 'Could not save the diary entry.');
    if (response.statusCode == 200 || response.statusCode == 201) {
      return DiaryEntry.fromJson(jsonDecode(response.body));
    }
    throw Exception('The diary API returned an unexpected response.');
  }

  static Future<DiaryEntry> updateEntry(
    int id,
    String content, {
    String? title,
    String? mood,
  }) async {
    final url = Uri.parse('${ApiService.baseUrl}/diary/$id');
    final headers = await ApiService.getHeaders();
    final response = await http.patch(
      url,
      headers: headers,
      body: jsonEncode({'content': content, 'title': title, 'mood': mood}),
    );
    await ApiService.ensureSuccess(response, 'Could not update the diary entry.');
    if (response.statusCode == 200) {
      return DiaryEntry.fromJson(jsonDecode(response.body));
    }
    throw Exception('The diary API returned an unexpected response.');
  }

  static Future<void> deleteEntry(int id) async {
    final url = Uri.parse('${ApiService.baseUrl}/diary/$id');
    final headers = await ApiService.getHeaders();
    final response = await http.delete(url, headers: headers);
    await ApiService.ensureSuccess(
      response,
      'Could not delete the diary entry.',
      acceptedStatusCodes: const {204},
    );
    if (response.statusCode != 204) {
      throw Exception('Failed to delete diary entry');
    }
  }
}
