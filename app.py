"""
GitHub MCDM + ML Analizi - Flask Dashboard

Bu modül, MCDM ve ML analiz sonuçlarını web tabanlı dashboard'da görselleştirir.

"""

from flask import Flask, render_template, jsonify
import json
import numpy as np
from scipy.stats import kendalltau
from analysis_pro import main, CRITERIA, SAATY_MATRIX, calculate_CR

app = Flask(__name__)

# Global cache
cached_results = None


def get_analysis_results():
    """Analiz sonuçlarını cache'den alır veya hesaplar."""
    global cached_results
    if cached_results is None:
        cached_results = main()
    return cached_results


def get_project_metrics(results, name):
    """
    Proje adına göre doğru metrikleri bulur.
    
    Bu fonksiyon, sıralanmış sonuçlarla orijinal veri arasındaki
    index uyumsuzluğunu çözer.
    """
    try:
        # Proje adının orijinal index'ini bul
        original_index = results['names'].index(name)
        data_row = results['data'][original_index]
        
        return {
            'stars': int(data_row[0]),
            'forks': int(data_row[1]),
            'contributors': int(data_row[2]),
            'commits': int(data_row[3]),
            'days_since_update': int(data_row[4]),
            'watchers': int(data_row[5]),
            'age_days': int(data_row[6])
        }
    except (ValueError, IndexError):
        return {
            'stars': 0,
            'forks': 0,
            'contributors': 0,
            'commits': 0,
            'days_since_update': 0,
            'watchers': 0,
            'age_days': 0
        }


def calculate_dynamic_stats(results):
    """İstatistikleri dinamik olarak hesaplar."""
    
    # CR hesapla
    CR, lambda_max, CI = calculate_CR(SAATY_MATRIX)
    
    # Korelasyon hesapla
    tau_classic_fuzzy, _ = kendalltau(
        results['scores']['topsis_classic'], 
        results['scores']['topsis_fuzzy']
    )
    tau_fuzzy_vikor, _ = kendalltau(
        results['scores']['topsis_fuzzy'], 
        results['scores']['vikor']
    )
    avg_correlation = (tau_classic_fuzzy + tau_fuzzy_vikor) / 2
    
    return {
        'cr_value': round(CR, 4),
        'lambda_max': round(lambda_max, 4),
        'ci_value': round(CI, 4),
        'correlation': round(avg_correlation, 3)
    }


def get_ml_results():
    """
    ML model sonuçlarını döndürür.
    Bu veriler ml_model.py çalıştırıldığında elde edilen sonuçlardır.
    """
    return {
        'models': {
            'Linear Regression': {
                'r2': 0.9895,
                'mae': 0.0080,
                'rmse': 0.0109,
                'cv': '0.994±0.002'
            },
            'Ridge Regression': {
                'r2': 0.9902,
                'mae': 0.0079,
                'rmse': 0.0106,
                'cv': '0.995±0.002'
            },
            'Random Forest': {
                'r2': 0.9553,
                'mae': 0.0135,
                'rmse': 0.0226,
                'cv': '0.942±0.030'
            },
            'Gradient Boosting': {
                'r2': 0.9578,
                'mae': 0.0134,
                'rmse': 0.0219,
                'cv': '0.924±0.039'
            },
            'XGBoost': {
                'r2': 0.9637,
                'mae': 0.0115,
                'rmse': 0.0203,
                'cv': '0.936±0.029'
            }
        },
        'best_model': 'Ridge Regression',
        'best_r2': 0.9902,
        'feature_importance': [
            {'name': 'Watchers', 'importance': 26.93},
            {'name': 'Stars', 'importance': 26.93},
            {'name': 'Forks', 'importance': 17.16},
            {'name': 'Contributors', 'importance': 4.18},
            {'name': 'Commits', 'importance': 4.09},
            {'name': 'Commit Freshness', 'importance': 4.07},
            {'name': 'Forks/Star', 'importance': 3.28},
            {'name': 'Contributors/Fork', 'importance': 3.08},
            {'name': 'Commits/Contributor', 'importance': 3.06},
            {'name': 'Stars/Day', 'importance': 2.57}
        ],
        'training_size': 103,
        'test_size': 26,
        'total_features': 14
    }


@app.route('/')
def dashboard():
    """Ana dashboard sayfası."""
    try:
        results = get_analysis_results()
        
        if results is None:
            return render_template('error.html', message="Analiz verileri yüklenemedi!"), 500
        
        # Top 20 projeler - DOĞRU INDEX İLE
        top_20 = []
        for i, (name, score) in enumerate(results['results'][:20]):
            metrics = get_project_metrics(results, name)
            top_20.append({
                'rank': i + 1,
                'name': name,
                'score': round(score * 100, 2),
                'stars': metrics['stars'],
                'forks': metrics['forks'],
                'contributors': metrics['contributors'],
                'commits': metrics['commits']
            })
        
        # Ağırlıklar
        weights = {
            'classic': [round(w * 100, 2) for w in results['weights']['classic'].tolist()],
            'fuzzy': [round(w * 100, 2) for w in results['weights']['fuzzy'].tolist()],
            'entropy': [round(w * 100, 2) for w in results['weights']['entropy'].tolist()]
        }
        
        # Dinamik istatistikler
        dynamic_stats = calculate_dynamic_stats(results)
        
        stats = {
            'total_projects': len(results['names']),
            'cr_value': dynamic_stats['cr_value'],
            'correlation': dynamic_stats['correlation'],
            'methods': 3,
            'top_project': results['results'][0][0],
            'top_score': round(results['results'][0][1] * 100, 2)
        }
        
        # Korelasyon matrisi (heatmap için)
        corr_matrix = []
        methods = ['topsis_classic', 'topsis_fuzzy', 'vikor']
        for m1 in methods:
            row = []
            for m2 in methods:
                if m1 == m2:
                    row.append(1.0)
                else:
                    tau, _ = kendalltau(results['scores'][m1], results['scores'][m2])
                    row.append(round(tau, 3))
            corr_matrix.append(row)
        
        # ML sonuçları
        ml_results = get_ml_results()
        
        return render_template('dashboard.html',
                             top_20=json.dumps(top_20),
                             weights=json.dumps(weights),
                             criteria=json.dumps(CRITERIA),
                             stats=stats,
                             corr_matrix=json.dumps(corr_matrix),
                             ml_results=ml_results,
                             ml_results_json=json.dumps(ml_results))
    
    except Exception as e:
        print(f"❌ Dashboard hatası: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', message=str(e)), 500


@app.route('/api/data')
def api_data():
    """REST API endpoint - JSON veri döner."""
    try:
        results = get_analysis_results()
        
        if results is None:
            return jsonify({'success': False, 'error': 'Veri yüklenemedi'}), 500
        
        # Top 10 projeler
        top_10 = []
        for i, (name, score) in enumerate(results['results'][:10]):
            metrics = get_project_metrics(results, name)
            top_10.append({
                'rank': i + 1,
                'name': name,
                'score': round(score * 100, 2),
                'stars': metrics['stars'],
                'forks': metrics['forks']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'total_projects': len(results['names']),
                'top_project': results['results'][0][0],
                'top_score': round(results['results'][0][1] * 100, 2),
                'top_10': top_10,
                'weights': {
                    'classic': [round(w * 100, 2) for w in results['weights']['classic'].tolist()],
                    'fuzzy': [round(w * 100, 2) for w in results['weights']['fuzzy'].tolist()]
                }
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ml')
def api_ml():
    """ML sonuçları API endpoint."""
    return jsonify(get_ml_results())


@app.route('/api/refresh')
def refresh_data():
    """Cache'i temizler ve veriyi yeniden yükler."""
    global cached_results
    cached_results = None
    
    try:
        results = get_analysis_results()
        return jsonify({
            'success': True,
            'message': 'Veriler yenilendi',
            'total_projects': len(results['names'])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    """404 hata sayfası."""
    return render_template('error.html', message="Sayfa bulunamadı!"), 404


@app.errorhandler(500)
def server_error(e):
    """500 hata sayfası."""
    return render_template('error.html', message="Sunucu hatası!"), 500


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 GITHUB MCDM + ML DASHBOARD")
    print("="*50)
    print("📍 Tarayıcıda aç: http://127.0.0.1:5000")
    print("📊 API endpoint:  http://127.0.0.1:5000/api/data")
    print("🤖 ML API:        http://127.0.0.1:5000/api/ml")
    print("🔄 Yenile:        http://127.0.0.1:5000/api/refresh")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)














