import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../providers/auth_provider.dart';
import 'login_screen.dart';
import 'home_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  Future<void> _submitRegister() async {
    if (_emailController.text.trim().isEmpty || _passwordController.text.isEmpty) return;
    try {
      await Provider.of<AuthProvider>(context, listen: false).register(
        _emailController.text.trim(), _passwordController.text, _nameController.text.trim());
      if (mounted) {
        Navigator.of(context).pushReplacement(PageRouteBuilder(
          pageBuilder: (_, __, ___) => const HomeScreen(),
          transitionsBuilder: (_, animation, __, child) => FadeTransition(opacity: animation, child: child),
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(e.toString()), backgroundColor: Colors.redAccent));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = Provider.of<AuthProvider>(context).isLoading;
    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF2C5364), Color(0xFF203A43), Color(0xFF0F2027)],
            begin: Alignment.topLeft, end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 32.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Join Solvyn',
                    style: GoogleFonts.outfit(fontSize: 48, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 2),
                  ).animate().fadeIn(duration: 800.ms).slideX(begin: -0.2),
                  const SizedBox(height: 8),
                  Text('Start your AI journey today.',
                    style: GoogleFonts.inter(fontSize: 16, color: Colors.white70),
                  ).animate().fadeIn(delay: 300.ms, duration: 800.ms),
                  const SizedBox(height: 48),
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: Colors.white.withOpacity(0.2)),
                      boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 20, offset: const Offset(0, 10))],
                    ),
                    child: Column(
                      children: [
                        TextField(
                          controller: _nameController, style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            labelText: 'Full Name', labelStyle: const TextStyle(color: Colors.white54),
                            enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white.withOpacity(0.3)), borderRadius: BorderRadius.circular(12)),
                            focusedBorder: OutlineInputBorder(borderSide: const BorderSide(color: Colors.cyanAccent), borderRadius: BorderRadius.circular(12)),
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _emailController, style: const TextStyle(color: Colors.white),
                          keyboardType: TextInputType.emailAddress,
                          decoration: InputDecoration(
                            labelText: 'Email', labelStyle: const TextStyle(color: Colors.white54),
                            enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white.withOpacity(0.3)), borderRadius: BorderRadius.circular(12)),
                            focusedBorder: OutlineInputBorder(borderSide: const BorderSide(color: Colors.cyanAccent), borderRadius: BorderRadius.circular(12)),
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _passwordController, style: const TextStyle(color: Colors.white), obscureText: true,
                          decoration: InputDecoration(
                            labelText: 'Password', labelStyle: const TextStyle(color: Colors.white54),
                            enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white.withOpacity(0.3)), borderRadius: BorderRadius.circular(12)),
                            focusedBorder: OutlineInputBorder(borderSide: const BorderSide(color: Colors.cyanAccent), borderRadius: BorderRadius.circular(12)),
                          ),
                        ),
                        const SizedBox(height: 32),
                        isLoading
                          ? const CircularProgressIndicator(color: Colors.cyanAccent)
                          : SizedBox(
                              width: double.infinity, height: 50,
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.cyanAccent, foregroundColor: Colors.black87,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                ),
                                onPressed: _submitRegister,
                                child: Text('Register', style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold)),
                              ),
                            ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 500.ms, duration: 800.ms).slideX(begin: 0.1),
                  const SizedBox(height: 24),
                  TextButton(
                    onPressed: () => Navigator.of(context).pushReplacement(PageRouteBuilder(
                      pageBuilder: (_, __, ___) => const LoginScreen(),
                      transitionsBuilder: (_, anim, __, child) => FadeTransition(opacity: anim, child: child),
                    )),
                    child: Text("Already have an account? Login", style: GoogleFonts.inter(color: Colors.cyanAccent)),
                  ).animate().fadeIn(delay: 1000.ms),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
