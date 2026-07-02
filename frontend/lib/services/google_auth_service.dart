import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter/foundation.dart';

class GoogleAuthResult {
  final String? idToken;
  final String? accessToken;

  GoogleAuthResult({this.idToken, this.accessToken});

  bool get hasToken => idToken != null || accessToken != null;
}

class GoogleAuthService {
  static final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email', 'profile', 'openid'],
    clientId: kIsWeb
        ? "138791352054-srdkgo2h3sm0i9irl7a2o2q99avkc9b5.apps.googleusercontent.com"
        : null,
  );

  static Future<GoogleAuthResult?> signIn() async {
    try {
      final account = await _googleSignIn.signIn();
      if (account == null) {
        print("Google sign-in: user cancelled");
        return null;
      }

      final auth = await account.authentication;

      print("Google sign-in success:");
      print("  idToken: ${auth.idToken != null ? 'PRESENT' : 'NULL'}");
      print("  accessToken: ${auth.accessToken != null ? 'PRESENT' : 'NULL'}");

      return GoogleAuthResult(
        idToken: auth.idToken,
        accessToken: auth.accessToken,
      );
    } catch (e) {
      print("Google sign-in failed: $e");
      return null;
    }
  }

  static Future<String?> signInAndGetIdToken() async {
    final result = await signIn();
    return result?.idToken;
  }
}
