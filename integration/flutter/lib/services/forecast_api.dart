// FarmNex forecast calls. Copy to your Flutter app: lib/services/forecast_api.dart
//
// The app talks ONLY to your FarmNex backend (never directly to the forecaster), and sends the
// farmer's Supabase login token so the backend knows who is asking.
//
// pubspec.yaml needs:  http: ^1.2.0   and   supabase_flutter (you already use it).

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

class ForecastApi {
  ForecastApi({required this.backendUrl});

  /// Your backend's address, e.g. 'https://api.farmnex.app' (no slash at the end).
  /// Android emulator talking to a backend on your own PC: 'http://10.0.2.2:8000'.
  final String backendUrl;

  Map<String, String> _headers() {
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<Map<String, dynamic>> _get(String path, Map<String, String> query) async {
    final uri = Uri.parse('$backendUrl$path').replace(queryParameters: query);
    final res = await http.get(uri, headers: _headers()).timeout(const Duration(seconds: 100));
    return _decode(res);
  }

  Map<String, dynamic> _decode(http.Response res) {
    final body = jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) {
      // The backend always sends {"detail": "..."} in simple words; show it to the farmer.
      final msg = body is Map && body['detail'] != null ? '${body['detail']}' : 'Error ${res.statusCode}';
      throw ForecastException(msg, res.statusCode);
    }
    return body as Map<String, dynamic>;
  }

  /// Lists for dropdowns: meta['markets'] (each has 'market', 'district', 'crops'),
  /// meta['crops'], meta['districts'], meta['data_as_of'], meta['attribution'].
  Future<Map<String, dynamic>> getMeta() => _get('/forecast/meta', {});

  /// Price for the next [days] days. result['days'] is a list of
  /// {'date', 'p10' (low), 'p50' (expected), 'p90' (high), 'likely_closed'}; prices are Rs/quintal.
  Future<Map<String, dynamic>> getPriceForecast(String market, String crop, {int days = 3}) =>
      _get('/forecast/price', {'market': market, 'crop': crop, 'days': '$days'});

  /// result['items']: one per crop with 'signal' = HIGH / NORMAL / LOW and 'reason'.
  Future<Map<String, dynamic>> getDemand(String district) =>
      _get('/forecast/demand', {'district': district});

  /// Where and when to sell. result['best'] has 'market', 'best_day', 'asking_price',
  /// 'floor_price', 'net_total', 'reason'. result['best'] is null if no market is in range.
  Future<Map<String, dynamic>> getSellOptions({
    required double lat,
    required double lon,
    required String crop,
    required double qtyQuintal,
    double? radiusKm,
  }) async {
    final res = await http
        .post(Uri.parse('$backendUrl/forecast/sell-options'),
            headers: _headers(),
            body: jsonEncode({
              'lat': lat,
              'lon': lon,
              'crop': crop,
              'qty_quintal': qtyQuintal,
              if (radiusKm != null) 'radius_km': radiusKm,
            }))
        .timeout(const Duration(seconds: 100));
    return _decode(res);
  }

  /// Which crop to sow. result['items']: {'rank', 'crop', 'harvest_month', 'expected_price', 'reason'}.
  Future<Map<String, dynamic>> getCropSuggestions(String district, int sowingMonth, {int k = 5}) =>
      _get('/forecast/crops', {'district': district, 'sowing_month': '$sowingMonth', 'k': '$k'});
}

class ForecastException implements Exception {
  ForecastException(this.message, this.statusCode);
  final String message;
  final int statusCode;
  @override
  String toString() => message;
}
