"""
GitHub MCDM Analizi - Görselleştirme Modülü

Bu modül, MCDM analiz sonuçlarını görselleştirir ve
yüksek çözünürlüklü grafikler oluşturur.

Grafikler:
    - Kriter ağırlıkları karşılaştırması (Bar + Radar)
    - Top 10 proje sıralaması
    - Yöntemler arası korelasyon heatmap
    - Kriter dağılımları (Box Plot)
    - Sensitivity analysis

"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.stats import kendalltau, spearmanr, rankdata
from analysis_pro import main, CRITERIA, IMPACTS, run_topsis
import warnings
warnings.filterwarnings('ignore')

# Türkçe karakter ve font ayarları
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300


def calculate_correlation_matrix(scores_dict: dict) -> tuple:
    """
    Yöntemler arası korelasyon matrisini hesaplar.
    
    Parameters:
    -----------
    scores_dict : dict
        Yöntem adı -> skorlar
        
    Returns:
    --------
    tuple: (corr_matrix, method_names)
    """
    methods = list(scores_dict.keys())
    n = len(methods)
    corr_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i == j:
                corr_matrix[i, j] = 1.0
            else:
                tau, _ = kendalltau(scores_dict[methods[i]], scores_dict[methods[j]])
                corr_matrix[i, j] = tau
    
    return corr_matrix, methods


def calculate_sensitivity_data(data: np.ndarray, base_weights: np.ndarray) -> dict:
    """
    Sensitivity analysis verilerini dinamik olarak hesaplar.
    
    Parameters:
    -----------
    data : np.ndarray
        Karar matrisi
    base_weights : np.ndarray
        Temel ağırlıklar
        
    Returns:
    --------
    dict: Her kriter için ortalama korelasyon değeri
    """
    base_scores = run_topsis(data, base_weights)
    base_ranking = rankdata(-base_scores, method='min')
    
    sensitivity_results = {}
    
    for i, criterion in enumerate(CRITERIA):
        correlations = []
        
        for delta in [-0.10, -0.05, 0, 0.05, 0.10]:
            new_weight = base_weights[i] + delta
            
            if new_weight < 0 or new_weight > 1:
                continue
            
            test_weights = base_weights.copy()
            test_weights[i] = new_weight
            test_weights = test_weights / test_weights.sum()
            
            test_scores = run_topsis(data, test_weights)
            test_ranking = rankdata(-test_scores, method='min')
            
            corr, _ = spearmanr(base_ranking, test_ranking)
            correlations.append(corr)
        
        sensitivity_results[criterion] = np.mean(correlations)
    
    return sensitivity_results


def create_weights_comparison(results: dict, save_path: str = 'grafik_agirliklar.png'):
    """
    Kriter ağırlıkları karşılaştırma grafiği (Bar Chart).
    
    References:
    -----------
    Saaty, T.L. (1980). The Analytic Hierarchy Process.
    """
    try:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(CRITERIA))
        width = 0.25
        
        bars1 = ax.bar(x - width, results['weights']['classic']*100, width, 
                       label='Klasik AHP', color='#3498db', edgecolor='black', linewidth=0.5)
        bars2 = ax.bar(x, results['weights']['fuzzy']*100, width, 
                       label='Fuzzy AHP', color='#e74c3c', edgecolor='black', linewidth=0.5)
        bars3 = ax.bar(x + width, results['weights']['entropy']*100, width, 
                       label='Entropy', color='#2ecc71', edgecolor='black', linewidth=0.5)
        
        # Değerleri bar üzerine yaz
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.1f}%',
                           xy=(bar.get_x() + bar.get_width()/2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=8, fontweight='bold')
        
        ax.set_xlabel('Kriterler', fontsize=12, fontweight='bold')
        ax.set_ylabel('Ağırlık (%)', fontsize=12, fontweight='bold')
        ax.set_title('Kriter Ağırlıkları Karşılaştırması\n(Klasik AHP vs Fuzzy AHP vs Entropy)', 
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(CRITERIA, rotation=45, ha='right', fontsize=10)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, max(results['weights']['entropy'])*100 + 10)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"✅ Grafik kaydedildi: {save_path}")
        
    except Exception as e:
        print(f"❌ Ağırlık grafiği hatası: {e}")


def create_radar_chart(results: dict, save_path: str = 'grafik_radar.png'):
    """
    Kriter ağırlıkları radar grafiği.
    
    Radar grafik, çok boyutlu verilerin karşılaştırılması için kullanılır.
    """
    try:
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Açıları hesapla
        angles = np.linspace(0, 2*np.pi, len(CRITERIA), endpoint=False).tolist()
        
        # Verileri hazırla
        w_classic = (results['weights']['classic']*100).tolist()
        w_fuzzy = (results['weights']['fuzzy']*100).tolist()
        
        # Kapatmak için ilk değeri sona ekle
        angles += angles[:1]
        w_classic += w_classic[:1]
        w_fuzzy += w_fuzzy[:1]
        
        # Çizim
        ax.plot(angles, w_classic, 'o-', linewidth=2.5, label='Klasik AHP', 
                color='#3498db', markersize=8)
        ax.fill(angles, w_classic, alpha=0.25, color='#3498db')
        
        ax.plot(angles, w_fuzzy, 's-', linewidth=2.5, label='Fuzzy AHP', 
                color='#e74c3c', markersize=8)
        ax.fill(angles, w_fuzzy, alpha=0.25, color='#e74c3c')
        
        # Etiketler
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(CRITERIA, size=11, fontweight='bold')
        ax.set_ylim(0, 35)
        
        ax.set_title('Kriter Ağırlıkları - Radar Görünümü\n', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.1), fontsize=11)
        ax.grid(True, alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"✅ Grafik kaydedildi: {save_path}")
        
    except Exception as e:
        print(f"❌ Radar grafiği hatası: {e}")


def create_top_projects_chart(results: dict, top_n: int = 15, save_path: str = 'grafik_top_projeler.png'):
    """
    En başarılı projelerin yatay bar grafiği.
    """
    try:
        fig, ax = plt.subplots(figsize=(12, 10))
        
        top_projects = results['results'][:top_n]
        projects = [p[0].split('/')[-1] for p in top_projects]  # Sadece repo adı
        scores = [p[1]*100 for p in top_projects]
        
        # Renk skalası (yeşilden kırmızıya)
        colors = plt.cm.RdYlGn(np.linspace(0.9, 0.3, top_n))
        
        # Yatay bar
        bars = ax.barh(range(top_n), scores, color=colors, edgecolor='black', linewidth=0.5)
        
        # Y ekseni
        ax.set_yticks(range(top_n))
        ax.set_yticklabels(projects, fontsize=11)
        ax.invert_yaxis()  # En iyi üstte
        
        # X ekseni
        ax.set_xlabel('TOPSIS Skoru (%)', fontsize=12, fontweight='bold')
        ax.set_xlim(0, max(scores) + 10)
        
        # Başlık
        ax.set_title(f'En Başarılı {top_n} GitHub Projesi\n(Fuzzy AHP + TOPSIS)', 
                    fontsize=14, fontweight='bold')
        
        # Değerleri bar sonuna yaz
        for i, (bar, score) in enumerate(zip(bars, scores)):
            ax.text(score + 0.5, bar.get_y() + bar.get_height()/2, 
                   f'{score:.2f}%', va='center', fontsize=10, fontweight='bold')
        
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"✅ Grafik kaydedildi: {save_path}")
        
    except Exception as e:
        print(f"❌ Top projeler grafiği hatası: {e}")


def create_correlation_heatmap(results: dict, save_path: str = 'grafik_korelasyon.png'):
    """
    Yöntemler arası korelasyon heatmap'i.
    
    DİNAMİK olarak hesaplanır, hardcoded değil!
    
    References:
    -----------
    Kendall, M.G. (1938). A New Measure of Rank Correlation.
    """
    try:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Korelasyon matrisini DİNAMİK hesapla
        scores_dict = {
            'TOPSIS\n(Klasik AHP)': results['scores']['topsis_classic'],
            'TOPSIS\n(Fuzzy AHP)': results['scores']['topsis_fuzzy'],
            'VIKOR': results['scores']['vikor']
        }
        
        corr_matrix, methods = calculate_correlation_matrix(scores_dict)
        
        # Heatmap
        sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdYlGn',
                   xticklabels=methods, yticklabels=methods,
                   vmin=0.8, vmax=1.0, square=True, ax=ax,
                   annot_kws={'size': 14, 'weight': 'bold'},
                   cbar_kws={'label': 'Kendall Tau Korelasyonu', 'shrink': 0.8})
        
        ax.set_title("Yöntemler Arası Korelasyon Analizi\n(Kendall's Tau)", 
                    fontsize=14, fontweight='bold', pad=20)
        ax.tick_params(axis='both', labelsize=11)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"✅ Grafik kaydedildi: {save_path}")
        
    except Exception as e:
        print(f"❌ Korelasyon grafiği hatası: {e}")


def create_boxplot(results: dict, save_path: str = 'grafik_boxplot.png'):
    """
    Kriter değerlerinin box plot analizi.
    
    Box plot, veri dağılımını ve aykırı değerleri gösterir.
    
    References:
    -----------
    Tukey, J.W. (1977). Exploratory Data Analysis.
    """
    try:
        fig, axes = plt.subplots(2, 4, figsize=(18, 10))
        axes = axes.flatten()
        
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#34495e']
        
        for i, criterion in enumerate(CRITERIA):
            if i < 7:
                ax = axes[i]
                data_col = results['data'][:, i]
                
                bp = ax.boxplot(data_col, vert=True, patch_artist=True)
                bp['boxes'][0].set_facecolor(colors[i])
                bp['boxes'][0].set_alpha(0.7)
                
                # İstatistikler
                median = np.median(data_col)
                mean = np.mean(data_col)
                
                ax.set_title(f'{criterion}', fontsize=11, fontweight='bold')
                ax.set_ylabel('Değer', fontsize=10)
                ax.grid(True, alpha=0.3)
                
                # Median ve mean değerlerini göster
                ax.axhline(y=mean, color='red', linestyle='--', alpha=0.5, label=f'Ort: {mean:.0f}')
                ax.legend(loc='upper right', fontsize=8)
        
        # Son subplot'u gizle
        axes[7].axis('off')
        
        plt.suptitle('Kriter Değerlerinin Dağılımı - Box Plot Analizi\n', 
                    fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"✅ Grafik kaydedildi: {save_path}")
        
    except Exception as e:
        print(f"❌ Box plot hatası: {e}")


def create_sensitivity_chart(results: dict, save_path: str = 'grafik_sensitivity.png'):
    """
    Duyarlılık analizi grafiği.
    
    DİNAMİK olarak hesaplanır, hardcoded değil!
    
    References:
    -----------
    Triantaphyllou, E. (2000). Multi-Criteria Decision Making Methods.
    """
    try:
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Sensitivity verilerini DİNAMİK hesapla
        sensitivity_data = calculate_sensitivity_data(results['data'], results['weights']['fuzzy'])
        
        criteria = list(sensitivity_data.keys())
        values = list(sensitivity_data.values())
        
        # Renklendirme (stabil = yeşil, hassas = kırmızı)
        colors = ['#2ecc71' if v > 0.95 else '#e74c3c' for v in values]
        
        bars = ax.bar(range(len(criteria)), values, color=colors, 
                     edgecolor='black', linewidth=1.5, alpha=0.8)
        
        ax.set_xticks(range(len(criteria)))
        ax.set_xticklabels(criteria, rotation=45, ha='right', fontsize=11)
        ax.set_ylabel('Spearman Korelasyonu (ρ)', fontsize=12, fontweight='bold')
        ax.set_title('Duyarlılık Analizi\nKriter Ağırlık Değişimlerinin Sıralama Üzerindeki Etkisi', 
                    fontsize=14, fontweight='bold')
        
        # Y ekseni limitleri
        min_val = min(values)
        ax.set_ylim(min_val - 0.01, 1.0)
        
        # Eşik çizgisi
        ax.axhline(y=0.95, color='red', linestyle='--', linewidth=2, 
                  alpha=0.7, label='Stabilite Eşiği (ρ = 0.95)')
        
        # Değerleri bar üzerine yaz
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                   f'{value:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend(loc='lower right', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"✅ Grafik kaydedildi: {save_path}")
        
    except Exception as e:
        print(f"❌ Sensitivity grafiği hatası: {e}")


def create_combined_analysis(results: dict, save_path: str = 'analiz_sonuclari.png'):
    """
    Tüm analizleri tek bir görselde birleştirir (2x2 layout).
    """
    try:
        fig = plt.figure(figsize=(20, 16))
        
        # 1. Ağırlık Karşılaştırması (Sol Üst)
        ax1 = fig.add_subplot(2, 2, 1)
        x = np.arange(len(CRITERIA))
        width = 0.25
        
        ax1.bar(x - width, results['weights']['classic']*100, width, 
               label='Klasik AHP', color='#3498db')
        ax1.bar(x, results['weights']['fuzzy']*100, width, 
               label='Fuzzy AHP', color='#e74c3c')
        ax1.bar(x + width, results['weights']['entropy']*100, width, 
               label='Entropy', color='#2ecc71')
        
        ax1.set_xlabel('Kriterler', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Ağırlık (%)', fontsize=11, fontweight='bold')
        ax1.set_title('Kriter Ağırlıkları Karşılaştırması', fontsize=13, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(CRITERIA, rotation=45, ha='right', fontsize=9)
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. Radar Chart (Sağ Üst)
        ax2 = fig.add_subplot(2, 2, 2, projection='polar')
        angles = np.linspace(0, 2*np.pi, len(CRITERIA), endpoint=False).tolist()
        w_classic = (results['weights']['classic']*100).tolist()
        w_fuzzy = (results['weights']['fuzzy']*100).tolist()
        angles += angles[:1]
        w_classic += w_classic[:1]
        w_fuzzy += w_fuzzy[:1]
        
        ax2.plot(angles, w_classic, 'o-', linewidth=2, label='Klasik AHP', color='#3498db')
        ax2.fill(angles, w_classic, alpha=0.25, color='#3498db')
        ax2.plot(angles, w_fuzzy, 'o-', linewidth=2, label='Fuzzy AHP', color='#e74c3c')
        ax2.fill(angles, w_fuzzy, alpha=0.25, color='#e74c3c')
        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels(CRITERIA, size=9)
        ax2.set_ylim(0, 35)
        ax2.set_title('Radar Görünümü', fontsize=13, fontweight='bold', pad=20)
        ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        
        # 3. Top 10 Projeler (Sol Alt)
        ax3 = fig.add_subplot(2, 2, 3)
        top_10 = results['results'][:10]
        projects = [p[0].split('/')[-1][:18] for p in top_10]
        scores = [p[1]*100 for p in top_10]
        colors = plt.cm.RdYlGn(np.linspace(0.9, 0.3, 10))
        
        bars = ax3.barh(range(10), scores, color=colors, edgecolor='black', linewidth=0.5)
        ax3.set_yticks(range(10))
        ax3.set_yticklabels(projects, fontsize=10)
        ax3.invert_yaxis()
        ax3.set_xlabel('TOPSIS Skoru (%)', fontsize=11, fontweight='bold')
        ax3.set_title('En Başarılı 10 Proje', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='x')
        
        for bar, score in zip(bars, scores):
            ax3.text(score + 0.5, bar.get_y() + bar.get_height()/2, 
                    f'{score:.1f}%', va='center', fontsize=9, fontweight='bold')
        
        # 4. Korelasyon Heatmap (Sağ Alt)
        ax4 = fig.add_subplot(2, 2, 4)
        scores_dict = {
            'TOPSIS-C': results['scores']['topsis_classic'],
            'TOPSIS-F': results['scores']['topsis_fuzzy'],
            'VIKOR': results['scores']['vikor']
        }
        corr_matrix, methods = calculate_correlation_matrix(scores_dict)
        
        sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdYlGn',
                   xticklabels=methods, yticklabels=methods,
                   vmin=0.8, vmax=1.0, square=True, ax=ax4,
                   annot_kws={'size': 12, 'weight': 'bold'})
        ax4.set_title('Yöntemler Arası Korelasyon', fontsize=13, fontweight='bold')
        
        plt.suptitle('GitHub Açık Kaynak Projeleri - MCDM Analiz Sonuçları', 
                    fontsize=16, fontweight='bold', y=1.01)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"✅ Grafik kaydedildi: {save_path}")
        
    except Exception as e:
        print(f"❌ Combined grafik hatası: {e}")


def create_all_visualizations():
    """
    Tüm görselleştirmeleri oluşturur.
    
    Çıktılar:
        - analiz_sonuclari.png (Kombine 2x2)
        - grafik_agirliklar.png
        - grafik_radar.png
        - grafik_top_projeler.png
        - grafik_korelasyon.png
        - grafik_boxplot.png
        - grafik_sensitivity.png
    """
    print("\n" + "="*60)
    print("🎨 GÖRSELLEŞTİRMELER HAZIRLANIYOR")
    print("="*60)
    
    # Analysis'den verileri al
    results = main()
    
    if results is None:
        print("❌ Analiz verileri alınamadı!")
        return None
    
    # Tüm grafikleri oluştur
    create_combined_analysis(results)
    create_weights_comparison(results)
    create_radar_chart(results)
    create_top_projects_chart(results)
    create_correlation_heatmap(results)
    create_boxplot(results)
    create_sensitivity_chart(results)
    
    print("\n" + "="*60)
    print("✅ TÜM GÖRSELLEŞTİRMELER TAMAMLANDI!")
    print("="*60)
    print("   📊 Oluşturulan dosyalar:")
    print("      - analiz_sonuclari.png (Kombine)")
    print("      - grafik_agirliklar.png")
    print("      - grafik_radar.png")
    print("      - grafik_top_projeler.png")
    print("      - grafik_korelasyon.png")
    print("      - grafik_boxplot.png")
    print("      - grafik_sensitivity.png")
    
    return results


if __name__ == "__main__":
    create_all_visualizations()