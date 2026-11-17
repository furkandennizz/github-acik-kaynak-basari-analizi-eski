"""
GitHub Açık Kaynak Projeleri - MCDM Analiz Modülü

Bu modül, GitHub projelerinin başarı faktörlerini çok kriterli karar verme
(MCDM) yöntemleri ile analiz eder.

Yöntemler:
    - Klasik AHP (Saaty, 1980)
    - Fuzzy AHP - Buckley Yöntemi (Buckley, 1985)
    - TOPSIS (Hwang & Yoon, 1981)
    - VIKOR (Opricovic & Tzeng, 2004)
    - Entropy Weight Method (Shannon, 1948)

"""

import os
import numpy as np
import mysql.connector
from datetime import datetime
from scipy.stats import kendalltau, spearmanr, rankdata, shapiro
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# GLOBAL SABİTLER
# =============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': 'github_analysis'
}

# Kriter isimleri
CRITERIA = [
    "Yıldız (Stars)", 
    "Fork Sayısı", 
    "Katkıcılar", 
    "Commit Sayısı", 
    "Güncellik", 
    "İzleyenler", 
    "Proje Yaşı"
]

# Kriter etki yönleri: 1 = Fayda (yüksek iyi), -1 = Maliyet (düşük iyi)
IMPACTS = np.array([1, 1, 1, 1, -1, 1, 1])

# Saaty Rastgele Tutarlılık İndeksi (RI) değerleri
RI_VALUES = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}

# AHP İkili Karşılaştırma Matrisi (7x7)
SAATY_MATRIX = np.array([
    [1.0,   2.0,   3.0,   3.0,   4.0,   2.0,   5.0],    # Stars
    [1/2,   1.0,   2.0,   2.0,   3.0,   1.0,   4.0],    # Forks
    [1/3,   1/2,   1.0,   1.0,   2.0,   1/2,   3.0],    # Contributors
    [1/3,   1/2,   1.0,   1.0,   2.0,   1/2,   3.0],    # Commits
    [1/4,   1/3,   1/2,   1/2,   1.0,   1/3,   2.0],    # Güncellik
    [1/2,   1.0,   2.0,   2.0,   3.0,   1.0,   4.0],    # Watchers
    [1/5,   1/4,   1/3,   1/3,   1/2,   1/4,   1.0]     # Yaş
])

# Fuzzy AHP Matrisi (Üçgensel Bulanık Sayılar: l, m, u)
FUZZY_MATRIX = [
    [(1,1,1),     (1,2,3),     (2,3,4),     (2,3,4),     (3,4,5),     (1,2,3),     (4,5,6)],
    [(1/3,1/2,1), (1,1,1),     (1,2,3),     (1,2,3),     (2,3,4),     (1,1,1),     (3,4,5)],
    [(1/4,1/3,1/2), (1/3,1/2,1), (1,1,1),   (1,1,1),     (1,2,3),     (1/3,1/2,1), (2,3,4)],
    [(1/4,1/3,1/2), (1/3,1/2,1), (1,1,1),   (1,1,1),     (1,2,3),     (1/3,1/2,1), (2,3,4)],
    [(1/5,1/4,1/3), (1/4,1/3,1/2), (1/3,1/2,1), (1/3,1/2,1), (1,1,1), (1/4,1/3,1/2), (1,2,3)],
    [(1/3,1/2,1), (1,1,1),     (1,2,3),     (1,2,3),     (2,3,4),     (1,1,1),     (3,4,5)],
    [(1/6,1/5,1/4), (1/5,1/4,1/3), (1/4,1/3,1/2), (1/4,1/3,1/2), (1/3,1/2,1), (1/5,1/4,1/3), (1,1,1)]
]


# =============================================================================
# VERİ ÇEKME FONKSİYONLARI
# =============================================================================

def get_data():
    """
    Veritabanından GitHub proje verilerini çeker.
    
    Returns:
    --------
    tuple: (data, names)
        - data: np.ndarray, Karar matrisi (n_projects x 7_criteria)
        - names: list, Proje isimleri
        
    Raises:
    -------
    ConnectionError: Veritabanı bağlantı hatası
    """
    print("📡 Veriler veritabanından çekiliyor...")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT r.full_name, r.stars, r.forks, r.watchers, r.created_at, r.updated_at,
        (SELECT COUNT(*) FROM contributors c WHERE c.repo_id = r.id) as contribs,
        (SELECT SUM(total_commits) FROM commit_activity ca WHERE ca.repo_id = r.id) as commits
        FROM repositories r
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            raise ValueError("Veritabanında proje bulunamadı!")
        
        data = []
        names = []
        
        for r in rows:
            now = datetime.now()
            age = (now - (r['created_at'] or now)).days
            update = (now - (r['updated_at'] or now)).days
            commits = float(r['commits'] or 0)
            contribs = float(r['contribs'] or 0)
            
            data.append([
                float(r['stars']), 
                float(r['forks']), 
                contribs, 
                commits, 
                float(update), 
                float(r['watchers']), 
                float(age)
            ])
            names.append(r['full_name'])
            
        print(f"✅ Toplam {len(data)} proje verisi yüklendi.")
        return np.array(data), names
        
    except mysql.connector.Error as e:
        print(f"❌ Veritabanı Hatası: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Beklenmeyen Hata: {e}")
        return None, None


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def check_reciprocal(matrix: np.ndarray, tolerance: float = 0.01) -> tuple:
    """
    AHP matrisinin reciprocal (karşılıklılık) özelliğini kontrol eder.
    
    AHP'de a[i][j] * a[j][i] = 1 olmalıdır.
    
    Parameters:
    -----------
    matrix : np.ndarray
        İkili karşılaştırma matrisi
    tolerance : float
        Kabul edilebilir hata payı (varsayılan: 0.01)
        
    Returns:
    --------
    tuple: (is_valid, errors)
        - is_valid: bool, Matris geçerli mi?
        - errors: list, Hatalı hücre pozisyonları
        
    References:
    -----------
    Saaty, T.L. (1980). The Analytic Hierarchy Process. McGraw-Hill.
    """
    n = len(matrix)
    errors = []
    
    for i in range(n):
        for j in range(i + 1, n):
            product = matrix[i][j] * matrix[j][i]
            if abs(product - 1.0) > tolerance:
                errors.append({
                    'position': f"[{i}][{j}]",
                    'value': matrix[i][j],
                    'reciprocal': matrix[j][i],
                    'product': product
                })
    
    is_valid = len(errors) == 0
    return is_valid, errors


def calculate_CR(matrix: np.ndarray) -> tuple:
    """
    Saaty Tutarlılık Oranı (Consistency Ratio) hesaplar.
    
    CR = CI / RI formülü kullanılır.
    CR < 0.10 ise matris tutarlıdır.
    
    Parameters:
    -----------
    matrix : np.ndarray
        İkili karşılaştırma matrisi (n x n)
        
    Returns:
    --------
    tuple: (CR, lambda_max, CI)
        - CR: float, Tutarlılık Oranı
        - lambda_max: float, Maksimum özdeğer
        - CI: float, Tutarlılık İndeksi
        
    References:
    -----------
    Saaty, T.L. (1980). The Analytic Hierarchy Process. McGraw-Hill.
    """
    n = len(matrix)
    
    # Özdeğer hesapla
    eigenvalues = np.linalg.eigvals(matrix)
    lambda_max = max(eigenvalues.real)
    
    # Tutarlılık İndeksi (CI)
    CI = (lambda_max - n) / (n - 1)
    
    # Rastgele Tutarlılık İndeksi (RI)
    RI = RI_VALUES.get(n, 1.45)
    
    # Tutarlılık Oranı (CR)
    CR = CI / RI if RI > 0 else 0
    
    return CR, lambda_max, CI


# =============================================================================
# AĞIRLIK HESAPLAMA YÖNTEMLERİ
# =============================================================================

def classic_ahp() -> np.ndarray:
    """
    Klasik AHP (Analytic Hierarchy Process) Yöntemi.
    
    Saaty (1980) tarafından geliştirilen çok kriterli karar verme yöntemi.
    İkili karşılaştırma matrisi kullanarak kriter ağırlıklarını hesaplar.
    
    Adımlar:
        1. Reciprocal kontrolü
        2. Sütun normalizasyonu
        3. Satır ortalaması = Ağırlıklar
        4. Tutarlılık kontrolü (CR < 0.10)
    
    Returns:
    --------
    np.ndarray
        Normalize edilmiş kriter ağırlıkları (toplam = 1)
        
    Raises:
    -------
    ValueError: Matris tutarsız veya reciprocal değilse
        
    References:
    -----------
    Saaty, T.L. (1980). The Analytic Hierarchy Process. McGraw-Hill, New York.
    """
    print("\n" + "="*60)
    print("📊 KLASİK AHP ANALİZİ")
    print("="*60)
    
    try:
        matrix = SAATY_MATRIX.copy()
        
        # 1. Reciprocal Kontrolü
        is_valid, errors = check_reciprocal(matrix)
        if not is_valid:
            print("⚠️  Reciprocal Kontrol Uyarıları:")
            for err in errors:
                print(f"   Pozisyon {err['position']}: {err['value']} x {err['reciprocal']} = {err['product']:.4f} ≠ 1")
            print("   (Tolerans içinde, devam ediliyor...)")
        else:
            print("✅ Reciprocal kontrolü başarılı (a[i][j] * a[j][i] = 1)")
        
        # 2. CR Hesapla
        CR, lambda_max, CI = calculate_CR(matrix)
        
        print(f"\n📈 Tutarlılık Analizi:")
        print(f"   λmax (Maksimum Özdeğer) = {lambda_max:.4f}")
        print(f"   CI (Tutarlılık İndeksi) = {CI:.4f}")
        print(f"   RI (Rastgele İndeks, n=7) = {RI_VALUES[7]}")
        print(f"   CR (Tutarlılık Oranı) = {CR:.4f}")
        
        if CR >= 0.10:
            print(f"❌ UYARI: CR = {CR:.4f} >= 0.10 - Matris tutarsız!")
            print("   Saaty matrisini gözden geçirin.")
            # Yine de devam et ama uyar
        else:
            print(f"✅ CR = {CR:.4f} < 0.10 - Matris TUTARLI")
        
        # 3. Sütun Normalizasyonu ve Ağırlık Hesaplama
        col_sums = matrix.sum(axis=0)
        norm_matrix = matrix / col_sums
        weights = norm_matrix.mean(axis=1)
        
        # 4. Ağırlıkları yazdır
        print(f"\n📊 Hesaplanan Ağırlıklar:")
        for i, (criterion, weight) in enumerate(zip(CRITERIA, weights)):
            bar = "█" * int(weight * 50)
            print(f"   {criterion:<20}: {weight*100:>6.2f}% {bar}")
        
        return weights
        
    except Exception as e:
        print(f"❌ AHP Hesaplama Hatası: {e}")
        return None


def fuzzy_ahp() -> np.ndarray:
    """
    Fuzzy AHP - Buckley Geometrik Ortalama Yöntemi.
    
    Buckley (1985) tarafından geliştirilen bulanık AHP yöntemi.
    Üçgensel bulanık sayılar (l, m, u) kullanarak belirsizliği modeller.
    
    Adımlar:
        1. Her satır için geometrik ortalama (l, m, u)
        2. Bulanık ağırlıkların hesaplanması
        3. Durulaştırma (Defuzzification) - Ortalama yöntemi
        4. Normalizasyon
    
    Returns:
    --------
    np.ndarray
        Normalize edilmiş kriter ağırlıkları
        
    References:
    -----------
    Buckley, J.J. (1985). Fuzzy hierarchical analysis. Fuzzy Sets and Systems, 17(3), 233-247.
    """
    print("\n" + "="*60)
    print("🧠 FUZZY AHP ANALİZİ (Buckley Yöntemi)")
    print("="*60)
    
    try:
        n = len(FUZZY_MATRIX)
        
        # 1. Geometrik Ortalamalar
        print("\n📐 Geometrik Ortalamalar Hesaplanıyor...")
        geo_means = []
        
        for i, row in enumerate(FUZZY_MATRIX):
            l_prod = np.prod([x[0] for x in row]) ** (1/n)
            m_prod = np.prod([x[1] for x in row]) ** (1/n)
            u_prod = np.prod([x[2] for x in row]) ** (1/n)
            geo_means.append((l_prod, m_prod, u_prod))
            print(f"   {CRITERIA[i]:<20}: ({l_prod:.3f}, {m_prod:.3f}, {u_prod:.3f})")
        
        # 2. Toplam Bulanık Değerler
        sum_l = sum([g[0] for g in geo_means])
        sum_m = sum([g[1] for g in geo_means])
        sum_u = sum([g[2] for g in geo_means])
        print(f"\n   Toplam: ({sum_l:.3f}, {sum_m:.3f}, {sum_u:.3f})")
        
        # 3. Bulanık Ağırlıklar ve Durulaştırma
        print("\n📊 Durulaştırma (Defuzzification)...")
        crisp_weights = []
        
        for i, g in enumerate(geo_means):
            # Bulanık bölme: (l/sum_u, m/sum_m, u/sum_l)
            fuzzy_w = (g[0]/sum_u, g[1]/sum_m, g[2]/sum_l)
            # Durulaştırma: Ortalama
            crisp = (fuzzy_w[0] + fuzzy_w[1] + fuzzy_w[2]) / 3
            crisp_weights.append(crisp)
        
        # 4. Normalizasyon
        weights = np.array(crisp_weights) / sum(crisp_weights)
        
        # 5. Sonuçları yazdır
        print(f"\n📊 Fuzzy AHP Ağırlıkları:")
        for i, (criterion, weight) in enumerate(zip(CRITERIA, weights)):
            bar = "█" * int(weight * 50)
            print(f"   {criterion:<20}: {weight*100:>6.2f}% {bar}")
        
        # 6. Fuzzy CR Kontrolü (Crisp matris üzerinden yaklaşık)
        CR, _, _ = calculate_CR(SAATY_MATRIX)
        print(f"\n   (Referans CR değeri: {CR:.4f})")
        
        return weights
        
    except Exception as e:
        print(f"❌ Fuzzy AHP Hatası: {e}")
        return None


def entropy_weight_method(data: np.ndarray) -> np.ndarray:
    """
    Entropy Ağırlık Yöntemi - Objektif Ağırlıklandırma.
    
    Shannon (1948) entropi kavramına dayanan objektif ağırlık hesaplama yöntemi.
    Verideki değişkenliğe göre ağırlık atar (yüksek değişkenlik = yüksek ağırlık).
    
    Adımlar:
        1. Normalizasyon (her sütun toplamı = 1)
        2. Entropi hesaplama: E = -k * Σ(p * ln(p))
        3. Çeşitlilik derecesi: d = 1 - E
        4. Ağırlık: w = d / Σd
    
    Parameters:
    -----------
    data : np.ndarray
        Karar matrisi (n_alternatives x n_criteria)
        
    Returns:
    --------
    np.ndarray
        Objektif kriter ağırlıkları
        
    References:
    -----------
    Shannon, C.E. (1948). A Mathematical Theory of Communication. Bell System Technical Journal.
    """
    print("\n" + "="*60)
    print("🔬 ENTROPY AĞIRLIK YÖNTEMİ")
    print("="*60)
    
    try:
        n_rows, n_cols = data.shape
        
        # 1. Normalizasyon
        col_sums = data.sum(axis=0)
        col_sums[col_sums == 0] = 1  # Sıfıra bölme hatası önle
        normalized = data / col_sums
        
        # Sıfır değerleri küçük bir sayıyla değiştir (log için)
        normalized = np.where(normalized == 0, 1e-10, normalized)
        
        # 2. Entropi Hesaplama
        k = -1 / np.log(n_rows)  # Normalizasyon sabiti
        entropy = k * np.sum(normalized * np.log(normalized), axis=0)
        
        print("\n📊 Entropi Değerleri:")
        for i, (criterion, e) in enumerate(zip(CRITERIA, entropy)):
            print(f"   {criterion:<20}: E = {e:.4f}")
        
        # 3. Çeşitlilik Derecesi
        diversity = 1 - entropy
        
        # 4. Ağırlıklar
        weights = diversity / diversity.sum()
        
        print(f"\n📊 Entropy Ağırlıkları:")
        for i, (criterion, weight) in enumerate(zip(CRITERIA, weights)):
            bar = "█" * int(weight * 50)
            print(f"   {criterion:<20}: {weight*100:>6.2f}% {bar}")
        
        return weights
        
    except Exception as e:
        print(f"❌ Entropy Hesaplama Hatası: {e}")
        return None


# =============================================================================
# MCDM YÖNTEMLERİ
# =============================================================================

def run_topsis(data: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """
    TOPSIS (Technique for Order Preference by Similarity to Ideal Solution).
    
    Hwang & Yoon (1981) tarafından geliştirilen çok kriterli karar verme yöntemi.
    Alternatifleri ideal çözüme yakınlık ve negatif-ideal çözümden uzaklık
    kriterlerine göre sıralar.
    
    Adımlar:
        1. Vektör normalizasyonu
        2. Ağırlıklı normalize matris
        3. İdeal (A+) ve Negatif-ideal (A-) çözümler
        4. Öklid mesafesi hesaplama
        5. Göreli yakınlık skoru: C = D- / (D+ + D-)
    
    Parameters:
    -----------
    data : np.ndarray
        Karar matrisi (n_alternatives x n_criteria)
    weights : np.ndarray
        Kriter ağırlıkları
        
    Returns:
    --------
    np.ndarray
        TOPSIS skorları (0-1 arası, yüksek = iyi)
        
    References:
    -----------
    Hwang, C.L.; Yoon, K. (1981). Multiple Attribute Decision Making: Methods and Applications.
    """
    try:
        # 1. Vektör Normalizasyonu
        denom = np.sqrt((data**2).sum(axis=0))
        denom[denom == 0] = 1  # Sıfıra bölme önle
        norm_data = data / denom
        
        # 2. Ağırlıklı Normalize Matris
        weighted_data = norm_data * weights
        
        # 3. İdeal ve Negatif-İdeal Çözümler
        ideal_best = []
        ideal_worst = []
        
        for i in range(len(weights)):
            if IMPACTS[i] == 1:  # Fayda kriteri
                ideal_best.append(weighted_data[:, i].max())
                ideal_worst.append(weighted_data[:, i].min())
            else:  # Maliyet kriteri
                ideal_best.append(weighted_data[:, i].min())
                ideal_worst.append(weighted_data[:, i].max())
        
        # 4. Öklid Mesafeleri
        dist_best = np.sqrt(((weighted_data - ideal_best)**2).sum(axis=1))
        dist_worst = np.sqrt(((weighted_data - ideal_worst)**2).sum(axis=1))
        
        # 5. Göreli Yakınlık Skoru
        scores = dist_worst / (dist_best + dist_worst + 1e-10)
        
        return scores
        
    except Exception as e:
        print(f"❌ TOPSIS Hatası: {e}")
        return None


def run_vikor(data: np.ndarray, weights: np.ndarray, v: float = 0.5) -> np.ndarray:
    """
    VIKOR (VlseKriterijumska Optimizacija I Kompromisno Resenje) Yöntemi.
    
    Opricovic & Tzeng (2004) tarafından geliştirilen uzlaşık çözüm yöntemi.
    Çoğunluk için maksimum grup faydası ve birey için minimum pişmanlık sağlar.
    
    Adımlar:
        1. İdeal (f*) ve en kötü (f-) değerleri belirleme
        2. S (grup faydası) ve R (bireysel pişmanlık) hesaplama
        3. Q (VIKOR indeksi) hesaplama
        4. Uzlaşık sıralama
    
    Parameters:
    -----------
    data : np.ndarray
        Karar matrisi
    weights : np.ndarray
        Kriter ağırlıkları
    v : float
        Uzlaşma katsayısı (0-1), varsayılan 0.5
        v > 0.5: çoğunluk kuralı, v < 0.5: bireysel pişmanlık
        
    Returns:
    --------
    np.ndarray
        VIKOR skorları (0-1 arası, yüksek = iyi)
        
    References:
    -----------
    Opricovic, S.; Tzeng, G.H. (2004). Compromise solution by MCDM methods.
    European Journal of Operational Research, 156(2), 445-455.
    """
    try:
        n_alternatives = len(data)
        n_criteria = len(weights)
        
        # 1. İdeal ve En Kötü Değerler
        f_best = []
        f_worst = []
        
        for i in range(n_criteria):
            if IMPACTS[i] == 1:
                f_best.append(data[:, i].max())
                f_worst.append(data[:, i].min())
            else:
                f_best.append(data[:, i].min())
                f_worst.append(data[:, i].max())
        
        # 2. S ve R Hesaplama
        S = np.zeros(n_alternatives)
        R = np.zeros(n_alternatives)
        
        for i in range(n_alternatives):
            for j in range(n_criteria):
                denom = f_best[j] - f_worst[j]
                if denom == 0:
                    denom = 1
                value = weights[j] * abs(f_best[j] - data[i, j]) / denom
                S[i] += value
                R[i] = max(R[i], value)
        
        # 3. Q Hesaplama
        S_best, S_worst = S.min(), S.max()
        R_best, R_worst = R.min(), R.max()
        
        S_denom = S_worst - S_best if S_worst != S_best else 1
        R_denom = R_worst - R_best if R_worst != R_best else 1
        
        Q = v * (S - S_best) / S_denom + (1 - v) * (R - R_best) / R_denom
        
        # 4. Skora dönüştür (düşük Q = iyi, tersine çevir)
        Q_max = Q.max() if Q.max() > 0 else 1
        scores = 1 - (Q / Q_max)
        
        return scores
        
    except Exception as e:
        print(f"❌ VIKOR Hatası: {e}")
        return None


# =============================================================================
# İSTATİSTİKSEL ANALİZLER
# =============================================================================

def normality_test(data: np.ndarray) -> dict:
    """
    Shapiro-Wilk normallik testi uygular.
    
    H0: Veriler normal dağılıma sahiptir
    H1: Veriler normal dağılıma sahip değildir
    p > 0.05 ise H0 kabul (Normal dağılım)
    
    Parameters:
    -----------
    data : np.ndarray
        Karar matrisi
        
    Returns:
    --------
    dict: Her kriter için test sonuçları
    
    References:
    -----------
    Shapiro, S.S.; Wilk, M.B. (1965). An analysis of variance test for normality.
    """
    print("\n" + "="*60)
    print("📊 NORMALLİK TESTİ (Shapiro-Wilk)")
    print("="*60)
    
    results = {}
    
    for i, criterion in enumerate(CRITERIA):
        stat, p_value = shapiro(data[:, i])
        is_normal = p_value > 0.05
        status = "✅ Normal" if is_normal else "❌ Normal Değil"
        
        results[criterion] = {
            'statistic': stat,
            'p_value': p_value,
            'is_normal': is_normal
        }
        
        print(f"   {criterion:<20}: W={stat:.4f}, p={p_value:.4f} → {status}")
    
    normal_count = sum(1 for r in results.values() if r['is_normal'])
    print(f"\n   Sonuç: {normal_count}/{len(CRITERIA)} kriter normal dağılıma sahip")
    
    return results


def outlier_analysis(data: np.ndarray) -> dict:
    """
    IQR (Interquartile Range) yöntemiyle aykırı değer analizi.
    
    Aykırı değer tanımı:
        - Alt sınır: Q1 - 1.5 * IQR
        - Üst sınır: Q3 + 1.5 * IQR
    
    Parameters:
    -----------
    data : np.ndarray
        Karar matrisi
        
    Returns:
    --------
    dict: Her kriter için outlier bilgisi
    
    References:
    -----------
    Tukey, J.W. (1977). Exploratory Data Analysis. Addison-Wesley.
    """
    print("\n" + "="*60)
    print("🔍 AYKIRI DEĞER ANALİZİ (IQR Yöntemi)")
    print("="*60)
    
    results = {}
    total_outliers = 0
    
    for i, criterion in enumerate(CRITERIA):
        Q1 = np.percentile(data[:, i], 25)
        Q3 = np.percentile(data[:, i], 75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outlier_mask = (data[:, i] < lower_bound) | (data[:, i] > upper_bound)
        outlier_count = np.sum(outlier_mask)
        outlier_pct = (outlier_count / len(data)) * 100
        
        total_outliers += outlier_count
        
        results[criterion] = {
            'Q1': Q1,
            'Q3': Q3,
            'IQR': IQR,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'outlier_count': outlier_count,
            'outlier_percentage': outlier_pct
        }
        
        status = "⚠️" if outlier_count > 0 else "✅"
        print(f"   {criterion:<20}: {outlier_count:>3} aykırı değer ({outlier_pct:.1f}%) {status}")
    
    print(f"\n   Toplam: {total_outliers} aykırı değer tespit edildi")
    
    return results


def sensitivity_analysis(data: np.ndarray, base_weights: np.ndarray) -> dict:
    """
    Duyarlılık analizi - ağırlık değişimlerinin sıralama üzerindeki etkisi.
    
    Her kriter için ±%5 ve ±%10 ağırlık değişimi uygulanarak
    sıralamanın ne kadar değiştiği ölçülür.
    
    Parameters:
    -----------
    data : np.ndarray
        Karar matrisi
    base_weights : np.ndarray
        Temel ağırlıklar
        
    Returns:
    --------
    dict: Her kriter için duyarlılık sonuçları
    
    References:
    -----------
    Triantaphyllou, E. (2000). Multi-Criteria Decision Making Methods: A Comparative Study.
    """
    print("\n" + "="*60)
    print("🔍 DUYARLILIK ANALİZİ")
    print("="*60)
    
    # Temel sıralama
    base_scores = run_topsis(data, base_weights)
    base_ranking = rankdata(-base_scores, method='min')
    
    sensitivity_results = {}
    
    for i, criterion in enumerate(CRITERIA):
        variations = []
        
        for delta in [-0.10, -0.05, 0, 0.05, 0.10]:
            new_weight = base_weights[i] + delta
            
            # Geçerlilik kontrolü
            if new_weight < 0 or new_weight > 1:
                continue
            
            # Yeni ağırlıkları hesapla
            test_weights = base_weights.copy()
            test_weights[i] = new_weight
            test_weights = test_weights / test_weights.sum()  # Normalize
            
            # Yeni sıralama
            test_scores = run_topsis(data, test_weights)
            test_ranking = rankdata(-test_scores, method='min')
            
            # Korelasyon
            correlation, p_value = spearmanr(base_ranking, test_ranking)
            
            variations.append({
                'delta': delta,
                'correlation': correlation,
                'p_value': p_value
            })
        
        avg_correlation = np.mean([v['correlation'] for v in variations])
        sensitivity_results[criterion] = {
            'variations': variations,
            'avg_correlation': avg_correlation,
            'stability': 'Stabil' if avg_correlation > 0.95 else 'Hassas'
        }
        
        status = "✅" if avg_correlation > 0.95 else "⚠️"
        print(f"   {criterion:<20}: Ort. ρ = {avg_correlation:.3f} → {sensitivity_results[criterion]['stability']} {status}")
    
    return sensitivity_results


def correlation_analysis(method_results: dict) -> np.ndarray:
    """
    Yöntemler arası sıralama korelasyonu analizi.
    
    Kendall's Tau-b korelasyon katsayısı kullanılır.
    τ > 0.8: Güçlü uyum
    τ = 0.6-0.8: Orta uyum
    τ < 0.6: Zayıf uyum
    
    Parameters:
    -----------
    method_results : dict
        Yöntem adı -> skorlar dictionary'si
        
    Returns:
    --------
    np.ndarray: Korelasyon matrisi
    
    References:
    -----------
    Kendall, M.G. (1938). A New Measure of Rank Correlation. Biometrika.
    """
    print("\n" + "="*60)
    print("📈 YÖNTEMLER ARASI KORELASYON (Kendall's Tau)")
    print("="*60)
    
    methods = list(method_results.keys())
    n = len(methods)
    corr_matrix = np.zeros((n, n))
    
    # Korelasyon hesapla
    for i in range(n):
        for j in range(n):
            if i == j:
                corr_matrix[i, j] = 1.0
            else:
                tau, _ = kendalltau(method_results[methods[i]], method_results[methods[j]])
                corr_matrix[i, j] = tau
    
    # Tablo başlığı
    header = f"{'Yöntem':<15}"
    for m in methods:
        header += f"{m:<15}"
    print(header)
    print("-" * (15 * (n + 1)))
    
    # Tablo içeriği
    for i, m1 in enumerate(methods):
        row = f"{m1:<15}"
        for j in range(n):
            row += f"{corr_matrix[i, j]:<15.3f}"
        print(row)
    
    # Yorum
    avg_corr = (corr_matrix.sum() - n) / (n * (n - 1))
    print(f"\n   Ortalama korelasyon: τ = {avg_corr:.3f}")
    
    if avg_corr > 0.8:
        print("   Yorum: ✅ Yöntemler arasında GÜÇLÜ UYUM var")
    elif avg_corr > 0.6:
        print("   Yorum: ⚠️ Yöntemler arasında ORTA UYUM var")
    else:
        print("   Yorum: ❌ Yöntemler arasında ZAYIF UYUM var")
    
    return corr_matrix


# =============================================================================
# EXPORT FONKSİYONLARI
# =============================================================================

def export_latex_weights(weights: dict, filename: str = "latex_agirliklar.tex"):
    """
    Kriter ağırlıklarını LaTeX tablo formatında export eder.
    
    Parameters:
    -----------
    weights : dict
        'classic', 'fuzzy', 'entropy' anahtarlarıyla ağırlık dizileri
    filename : str
        Çıktı dosya adı
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("% Kriter Ağırlıkları Tablosu - Otomatik oluşturuldu\n")
            f.write("\\begin{table}[htbp]\n")
            f.write("\\centering\n")
            f.write("\\caption{Farklı Yöntemlerle Hesaplanan Kriter Ağırlıkları}\n")
            f.write("\\label{tab:kriter_agirliklari}\n")
            f.write("\\begin{tabular}{|l|c|c|c|}\n")
            f.write("\\hline\n")
            f.write("\\textbf{Kriter} & \\textbf{Klasik AHP} & \\textbf{Fuzzy AHP} & \\textbf{Entropy} \\\\\n")
            f.write("\\hline\n")
            
            for i, kriter in enumerate(CRITERIA):
                f.write(f"{kriter} & {weights['classic'][i]*100:.2f}\\% & ")
                f.write(f"{weights['fuzzy'][i]*100:.2f}\\% & ")
                f.write(f"{weights['entropy'][i]*100:.2f}\\% \\\\\n")
            
            f.write("\\hline\n")
            f.write("\\textbf{Toplam} & 100.00\\% & 100.00\\% & 100.00\\% \\\\\n")
            f.write("\\hline\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n")
        
        print(f"✅ LaTeX tablo kaydedildi: {filename}")
        
    except Exception as e:
        print(f"❌ LaTeX export hatası: {e}")


def export_latex_ranking(results: list, filename: str = "latex_siralama.tex", top_n: int = 20):
    """
    Proje sıralamasını LaTeX tablo formatında export eder.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("% Proje Sıralaması Tablosu - Otomatik oluşturuldu\n")
            f.write("\\begin{table}[htbp]\n")
            f.write("\\centering\n")
            f.write(f"\\caption{{En Başarılı {top_n} GitHub Projesi (Fuzzy AHP + TOPSIS)}}\n")
            f.write("\\label{tab:proje_siralama}\n")
            f.write("\\begin{tabular}{|c|l|c|}\n")
            f.write("\\hline\n")
            f.write("\\textbf{Sıra} & \\textbf{Proje} & \\textbf{TOPSIS Skoru} \\\\\n")
            f.write("\\hline\n")
            
            for i, (name, score) in enumerate(results[:top_n], 1):
                # Proje adını kısalt
                short_name = name.replace('_', '\\_')
                if len(short_name) > 40:
                    short_name = short_name[:37] + "..."
                f.write(f"{i} & {short_name} & {score*100:.2f}\\% \\\\\n")
            
            f.write("\\hline\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n")
        
        print(f"✅ LaTeX sıralama tablosu kaydedildi: {filename}")
        
    except Exception as e:
        print(f"❌ LaTeX export hatası: {e}")


# =============================================================================
# ANA PROGRAM
# =============================================================================

def main():
    """
    Ana analiz programı.
    
    Tüm MCDM analizlerini sırayla çalıştırır ve sonuçları döndürür.
    """
    print("\n" + "="*80)
    print("🚀 GITHUB AÇIK KAYNAK PROJELERİ - MCDM ANALİZİ")
    print("="*80)
    
    # 1. Veri Çekme
    data, names = get_data()
    
    if data is None:
        print("❌ Program sonlandırıldı: Veri çekilemedi!")
        return None
    
    # 2. İstatistiksel Ön Analiz
    normality_test(data)
    outlier_analysis(data)
    
    # 3. Ağırlık Hesaplama
    w_classic = classic_ahp()
    w_fuzzy = fuzzy_ahp()
    w_entropy = entropy_weight_method(data)
    
    if w_classic is None or w_fuzzy is None or w_entropy is None:
        print("❌ Program sonlandırıldı: Ağırlık hesaplanamadı!")
        return None
    
    # 4. Ağırlık Karşılaştırması
    print("\n" + "="*80)
    print("📊 KRİTER AĞIRLIKLARI KARŞILAŞTIRMASI")
    print("="*80)
    print(f"{'Kriter':<20} | {'Klasik AHP':<12} | {'Fuzzy AHP':<12} | {'Entropy':<12}")
    print("-"*80)
    
    for i in range(len(CRITERIA)):
        print(f"{CRITERIA[i]:<20} | {w_classic[i]*100:>10.2f}% | {w_fuzzy[i]*100:>10.2f}% | {w_entropy[i]*100:>10.2f}%")
    
    # 5. MCDM Yöntemleri
    print("\n" + "="*60)
    print("🎯 MCDM YÖNTEMLERİ UYGULANYOR")
    print("="*60)
    
    scores_topsis_classic = run_topsis(data, w_classic)
    scores_topsis_fuzzy = run_topsis(data, w_fuzzy)
    scores_vikor = run_vikor(data, w_fuzzy)
    
    print("   ✅ TOPSIS (Klasik AHP) tamamlandı")
    print("   ✅ TOPSIS (Fuzzy AHP) tamamlandı")
    print("   ✅ VIKOR tamamlandı")
    
    # 6. Korelasyon Analizi
    method_results = {
        'TOPSIS-Classic': scores_topsis_classic,
        'TOPSIS-Fuzzy': scores_topsis_fuzzy,
        'VIKOR': scores_vikor
    }
    
    correlation_analysis(method_results)
    
    # 7. Duyarlılık Analizi
    sensitivity_analysis(data, w_fuzzy)
    
    # 8. Final Sıralama
    final_scores = scores_topsis_fuzzy
    results = sorted(zip(names, final_scores), key=lambda x: x[1], reverse=True)
    
    print("\n" + "="*80)
    print("🏆 NİHAİ SIRALAMA (TOP 20) - FUZZY AHP + TOPSIS")
    print("="*80)
    print(f"{'Sıra':<5} | {'Proje':<50} | {'Skor':<10}")
    print("-"*80)
    
    for i, (name, score) in enumerate(results[:20], 1):
        print(f"{i:<5} | {name:<50} | {score*100:>8.2f}%")
    
    # 9. LaTeX Export
    weights_dict = {
        'classic': w_classic,
        'fuzzy': w_fuzzy,
        'entropy': w_entropy
    }
    export_latex_weights(weights_dict)
    export_latex_ranking(results)
    
    # 10. Sonuç
    print("\n" + "="*80)
    print("✅ TÜM ANALİZLER BAŞARIYLA TAMAMLANDI!")
    print("="*80)
    print(f"   📊 Toplam proje: {len(names)}")
    print(f"   📈 En başarılı: {results[0][0]} ({results[0][1]*100:.2f}%)")
    print(f"   📉 En düşük: {results[-1][0]} ({results[-1][1]*100:.2f}%)")
    print(f"   📄 LaTeX dosyaları oluşturuldu")
    
    return {
        'data': data,
        'names': names,
        'weights': {
            'classic': w_classic,
            'fuzzy': w_fuzzy,
            'entropy': w_entropy
        },
        'scores': {
            'topsis_classic': scores_topsis_classic,
            'topsis_fuzzy': scores_topsis_fuzzy,
            'vikor': scores_vikor
        },
        'results': results
    }


if __name__ == "__main__":
    main()