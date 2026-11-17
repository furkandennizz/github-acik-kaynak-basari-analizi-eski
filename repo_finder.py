import requests
import time
from config import GITHUB_TOKEN  # GITHUB_TOKEN ortam değişkeninden

class RepoFinder:
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com/search/repositories'
        print("RepoFinder hazır!")

    def search_repos(self, query, category, level, max_repos=10):
        """
        Belirli bir kategoride ve seviyede en popüler repoları bul
        """
        repos = []
        page = 1
        
        print(f"\nAranıyor: Kategori={category}, Seviye={level}")
        print(f"Sorgu: {query}")

        while len(repos) < max_repos:
            params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': max_repos, # Tek seferde max_repos kadar çek
                'page': page
            }

            try:
                response = requests.get(self.base_url, headers=self.headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    
                    if not items:
                        print("Daha fazla sonuç bulunamadı.")
                        break # Sonuç yoksa döngüden çık

                    for item in items:
                        if len(repos) >= max_repos:
                            break
                        
                        repo_info = {
                            'owner': item['owner']['login'],
                            'repo_name': item['name'],
                            'full_name': item['full_name'],
                            'stars': item['stargazers_count'],
                            'category': category,
                            'level': level
                        }
                        repos.append(repo_info)
                        print(f"  ✓ {item['full_name']} ({item['stargazers_count']:,} stars)")
                    
                    break # Sadece ilk sayfayı alıyoruz (max_repos kadar)

                else:
                    print(f"  Hata: {response.status_code}")
                    if 'rate limit' in response.text:
                        print("  Rate limit doldu! Bekleniyor...")
                        time.sleep(60)
                        continue # Sorguyu tekrar dene
                    break

            except Exception as e:
                print(f"  Exception: {e}")
                break
        
        print(f"  Bu seviye için {len(repos)} repo bulundu.")
        return repos

    def get_all_repos(self):
        """
        Tüm kategorilerden ve seviyelerden repo topla
        """
        all_repos = []

        # 5 Kategori, 3 Seviye = 15 sorgu = 150 repo (her biri 10 repo)
        categories_queries = [# 5 Kategori, 3 Seviye = 15 sorgu (Hedef 150 repo)
    
        # 1. Kategori: Web Frameworks (topic:frontend kullanacağız, daha genel)
        {'name': 'Web Frameworks', 'level': 'Çok Başarılı', 'query': 'topic:frontend stars:>50000', 'count': 10},
        {'name': 'Web Frameworks', 'level': 'Başarılı', 'query': 'topic:frontend stars:15000..50000', 'count': 10},
        {'name': 'Web Frameworks', 'level': 'Gelişmekte', 'query': 'topic:frontend stars:5000..15000', 'count': 10},

        # 2. Kategori: Machine Learning (Bu zaten 30 bulmuştu, kalsın)
        {'name': 'Machine Learning', 'level': 'Çok Başarılı', 'query': 'topic:machine-learning stars:>50000 language:Python', 'count': 10},
        {'name': 'Machine Learning', 'level': 'Başarılı', 'query': 'topic:machine-learning stars:10000..50000 language:Python', 'count': 10},
        {'name': 'Machine Learning', 'level': 'Gelişmekte', 'query': 'topic:machine-learning stars:2000..10000 language:Python', 'count': 10},

        # 3. Kategori: Backend Frameworks (topic:backend kullanacağız)
        {'name': 'Backend Frameworks', 'level': 'Çok Başarılı', 'query': 'topic:backend stars:>40000', 'count': 10},
        {'name': 'Backend Frameworks', 'level': 'Başarılı', 'query': 'topic:backend stars:10000..40000', 'count': 10},
        {'name': 'Backend Frameworks', 'level': 'Gelişmekte', 'query': 'topic:backend stars:3000..10000', 'count': 10},

        # 4. Kategori: Developer Tools (Bu da 30 bulmuştu, kalsın)
        {'name': 'Developer Tools', 'level': 'Çok Başarılı', 'query': 'topic:developer-tools stars:>40000', 'count': 10},
        {'name': 'Developer Tools', 'level': 'Başarılı', 'query': 'topic:developer-tools stars:10000..40000', 'count': 10},
        {'name': 'Developer Tools', 'level': 'Gelişmekte', 'query': 'topic:developer-tools stars:2000..10000', 'count': 10},

        # 5. Kategori: Mobile Development (topic:mobile kullanacağız)
        {'name': 'Mobile Development', 'level': 'Çok Başarılı', 'query': 'topic:mobile stars:>30000', 'count': 10},
        {'name': 'Mobile Development', 'level': 'Başarılı', 'query': 'topic:mobile stars:10000..30000', 'count': 10},
        {'name': 'Mobile Development', 'level': 'Gelişmekte', 'query': 'topic:mobile stars:3000..10000', 'count': 10},
    ]
            
        print(f"\n{'='*60}")
        print(f"TOPLAM 150 REPO BULUNACAK (15 sorgu x 10 repo)")
        print(f"{'='*60}")

        for query_info in categories_queries:
            repos = self.search_repos(
                query_info['query'], 
                query_info['name'],
                query_info['level'],
                query_info['count']
            )
            all_repos.extend(repos)
            print("--- Sorgular arası 3 saniye bekleniyor (rate limit için) ---")
            time.sleep(3) # GitHub API rate limit için bekle

        print(f"\n{'='*60}")
        print(f"REPO ARAMA BİTTİ!")
        print(f"Toplam {len(all_repos)} repo bulundu.")
        print(f"{'='*60}\n")
        return all_repos

    def save_to_file(self, repos, filename='repos_list.txt'):
        """
        Repo listesini dosyaya kaydet
        Format: owner,repo_name,category,level
        """
        with open(filename, 'w', encoding='utf-8') as f:
            for repo in repos:
                f.write(f"{repo['owner']},{repo['repo_name']},{repo['category']},{repo['level']}\n")
        
        print(f"✓ Liste '{filename}' dosyasına kaydedildi!")

# Ana program
if __name__ == "__main__":
    finder = RepoFinder()
    
    # 1. Repoları bul
    repos_list = finder.get_all_repos()
    
    # 2. Dosyaya kaydet
    finder.save_to_file(repos_list)
    
    # 3. Özet göster
    print("\nKategori Dağılımı Özeti:")
    categories = {}
    for repo in repos_list:
        cat = repo['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        print(f"  {cat}: {count} repo")