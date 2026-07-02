import 'package:flutter/material.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/signup_screen.dart';
import 'screens/diary/home_screen.dart';
import 'screens/diary/diary_write_screen.dart';
import 'screens/chat/chat_screen.dart';

void main() {
  runApp(SolvynApp());
}

class SolvynApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      initialRoute: "/login",
      routes: {
        "/login": (context) => LoginScreen(),
        "/signup": (context) => SignupScreen(),
        "/home": (context) => HomeScreen(),
        "/chat": (context) => ChatScreen(),
        "/write_diary": (context) => DiaryWriteScreen(),
      },
    );
  }
}
