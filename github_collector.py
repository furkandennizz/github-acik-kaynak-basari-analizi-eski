import os
import requests
import time
import mysql.connector
from datetime import datetime
from config import GITHUB_TOKEN
import json 

class GitHubCollector:
    def __init__(self):
        print("GitHubCollector (LİSTE MODU) başlatılıyor...")
        
        self.token = GITHUB_TOKEN
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            self.db = mysql.connector.connect(
                host='localhost',
                user='root',
                password=os.environ.get('MYSQL_PASSWORD', ''),
                database='github_analysis'
            )
            self.cursor = self.db.cursor()
            print("MySQL bağlantısı başarılı!")
        except Exception as e:
            print(f"MySQL bağlantı hatası: {e}")
            exit()
        
        print("GitHubCollector hazır!\n")
    
    def convert_github_date(self, date_str):
        if not date_str: return None
        return date_str.replace('Z', '').replace('T', ' ')

    def get_repo_info(self, owner, repo):
        """Kriter 1, 2, 5, 6, 7"""
        url = f'{self.base_url}/repos/{owner}/{repo}'
        print(f"[1/3] Temel Bilgiler: {owner}/{repo}...")
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                repo_data = {
                    'owner': owner, 'repo_name': repo, 'full_name': data['full_name'],
                    'description': data['description'], 'stars': data['stargazers_count'],
                    'forks': data['forks_count'], 'watchers': data['watchers_count'],
                    'open_issues': data['open_issues_count'], 'language': data['language'],
                    'created_at': self.convert_github_date(data['created_at']), 
                    'updated_at': self.convert_github_date(data['updated_at']) 
                }
                print(f"  ✓ Bilgiler alındı ({data['stargazers_count']:,} stars)")
                return repo_data
            else:
                print(f"  HATA: {response.status_code}")
                return None
        except Exception as e:
            print(f"  HATA: {e}")
            return None
    
    def get_contributors(self, owner, repo, repo_id):
        """Kriter 3"""
        url = f'{self.base_url}/repos/{owner}/{repo}/contributors'
        params = {'per_page': 100}
        print(f"[2/3] Contributors...")
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                contributors = response.json()
                if not contributors: return
                
                self.cursor.execute("DELETE FROM contributors WHERE repo_id = %s", (repo_id,))
                sql = "INSERT INTO contributors (repo_id, login, contributions) VALUES (%s, %s, %s)"
                values = [(repo_id, u['login'], u['contributions']) for u in contributors if u.get('login')]
                
                if values:
                    self.cursor.executemany(sql, values)
                    self.db.commit()
                print(f"  ✓ {len(contributors)} kişi kaydedildi.")
        except Exception:
            pass

    def get_commit_activity(self, owner, repo, repo_id):
        """Kriter 4"""
        url = f'{self.base_url}/repos/{owner}/{repo}/stats/commit_activity'
        print(f"[3/3] Commit Activity...")
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 202: # GitHub hesaplıyor
                time.sleep(3)
                response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                weeks = response.json()
                if not weeks: return
                
                self.cursor.execute("DELETE FROM commit_activity WHERE repo_id = %s", (repo_id,))
                sql = "INSERT INTO commit_activity (repo_id, week_timestamp, total_commits) VALUES (%s, %s, %s)"
                values = [(repo_id, w['week'], w['total']) for w in weeks]
                
                if values:
                    self.cursor.executemany(sql, values)
                    self.db.commit()
                print(f"  ✓ Aktivite verisi kaydedildi.")
        except Exception:
            pass

    def save_to_db(self, repo_data):
        try:
            sql = """
            INSERT INTO repositories (owner, repo_name, full_name, description, stars, forks, watchers, open_issues, language, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE stars=VALUES(stars), forks=VALUES(forks), watchers=VALUES(watchers), open_issues=VALUES(open_issues), updated_at=VALUES(updated_at)
            """
            values = (repo_data['owner'], repo_data['repo_name'], repo_data['full_name'], repo_data['description'], repo_data['stars'], repo_data['forks'], repo_data['watchers'], repo_data['open_issues'], repo_data['language'], repo_data['created_at'], repo_data['updated_at'])
            self.cursor.execute(sql, values)
            self.db.commit()
            
            self.cursor.execute("SELECT id FROM repositories WHERE owner = %s AND repo_name = %s", (repo_data['owner'], repo_data['repo_name']))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"  DB HATA: {e}")
            return None
    
    def collect_repo_full(self, owner, repo):
        print(f"\n{'='*60}")
        repo_data = self.get_repo_info(owner, repo)
        if not repo_data: return False
        
        repo_id = self.save_to_db(repo_data)
        if not repo_id: return False
        
        time.sleep(1)
        self.get_contributors(owner, repo, repo_id)
        time.sleep(1)
        self.get_commit_activity(owner, repo, repo_id)
        print(f"--- {owner}/{repo} TAMAMLANDI ---")
        return True

    def close(self):
        self.cursor.close()
        self.db.close()
        print("\nBağlantı kapatıldı.")

def load_repos_from_file(filename='repos_list.txt'):
    repos = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    repos.append((parts[0], parts[1]))
        print(f"✓ '{filename}' dosyasından {len(repos)} repo yüklendi.")
    except FileNotFoundError:
        print(f"❌ HATA: '{filename}' yok!")
        return None
    return repos

if __name__ == "__main__":
    # BURASI ÇOK ÖNEMLİ: LİSTEDEN OKUYORUZ
    repo_list = load_repos_from_file('repos_list.txt')
    
    if repo_list:
        collector = GitHubCollector()
        total = len(repo_list)
        print(f"\nTOPLAM {total} REPO ÇEKİLECEK...")
        time.sleep(2)

        for i, (owner, repo) in enumerate(repo_list, 1):
            print(f"\n--- [{i}/{total}] ---")
            collector.collect_repo_full(owner, repo)
            time.sleep(2) # Rate limit bekleme
        
        collector.close()