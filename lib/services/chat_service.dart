import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';
import '../models/chat_message.dart';

class ChatService {
  static Future<List<ChatMessage>> getHistory() async {
    final url = Uri.parse('${ApiService.baseUrl}/ai/chat/history');
    final headers = await ApiService.getHeaders();
    final response = await http.get(url, headers: headers);
    await ApiService.ensureSuccess(response, 'Could not load chat history.');
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => ChatMessage.fromJson(json)).toList();
    }
    throw Exception('The chat API returned an unexpected response.');
  }

  static Future<Map<String, dynamic>> sendMessage(String content) async {
    final url = Uri.parse('${ApiService.baseUrl}/ai/chat');
    final headers = await ApiService.getHeaders();
    final response = await http.post(url, headers: headers, body: jsonEncode({'content': content}));
    await ApiService.ensureSuccess(response, 'Could not send your message.');
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('The chat API returned an unexpected response.');
  }
}
