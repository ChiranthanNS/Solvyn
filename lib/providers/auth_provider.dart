import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../services/auth_service.dart';

class AuthProvider with ChangeNotifier {
  String? _token;
  bool _isLoading = false;

  final GoogleSignIn _googleSignIn = GoogleSignIn(
    clientId: '138791352054-srdkgo2h3sm0i9irl7a2o2q99avkc9b5.apps.googleusercontent.com',
    scopes: ['email', 'profile', 'openid'],
  );

  String? get token => _token;
  bool get isAuthenticated => _token != null;
  bool get isLoading => _isLoading;

  Future<void> tryAutoLogin() async {
    final prefs = await SharedPreferences.getInstance();
    if (!prefs.containsKey('auth_token')) return;
    _token = prefs.getString('auth_token');
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();
    try {
      final res = await AuthService.login(email, password);
      _token = res['access_token'];
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', _token!);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> register(String email, String password, String name) async {
    _isLoading = true;
    notifyListeners();
    try {
      await AuthService.register(email, password, name: name);
      await login(email, password);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loginWithGoogle() async {
    _isLoading = true;
    notifyListeners();
    try {
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        _isLoading = false;
        notifyListeners();
        return;
      }
      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      final String? idToken = googleAuth.idToken;
      final String? accessToken = googleAuth.accessToken;
      Map<String, dynamic> res;
      if (idToken != null) {
        res = await AuthService.loginWithGoogle(idToken);
      } else if (accessToken != null) {
        res = await AuthService.loginWithGoogleAccessToken(accessToken);
      } else {
        throw Exception('Google sign-in failed: no token received.');
      }
      _token = res['access_token'];
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', _token!);
    } catch (e) {
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    _token = null;
    try {
      await _googleSignIn.signOut();
    } catch (e) {
      // Ignored
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    notifyListeners();
  }
}
