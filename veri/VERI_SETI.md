**VERİ SETİ AÇIKLAMA DOKÜMANI**

*GitHub Açık Kaynak Projeleri — MCDM + ML Analizi*

**1. Veri Setinin Hikayesi**

Bu veri seti, GitHub platformundaki açık kaynak projelerin çok kriterli değerlendirilmesi amacıyla oluşturulmuştur. GitHub, 100 milyonun üzerinde geliştirici ve 400 milyondan fazla repository barındıran dünyanın en büyük yazılım geliştirme platformudur. Açık kaynak projelerin başarısı genellikle yalnızca star (yıldız) sayısına bakılarak değerlendirilmektedir; ancak bu tek metrikli yaklaşım, projenin bakım durumu, topluluk gücü ve sürdürülebilirliği gibi kritik boyutları göz ardı etmektedir.

Bu çalışmada 129 açık kaynak proje, 9 farklı kategoriden (Web Frameworks, ML/AI, DevOps, Database, Security, Mobile, Programming Languages, Data Science, Cloud/Infrastructure) seçilmiştir. Projeler minimum 100 star filtresine tabi tutularak düşük profilli projeler elenmiştir. Veri seti, projelerin hem popülerlik hem de aktif geliştirme durumunu yansıtan 7 farklı metriği içermektedir.

**2. Veri Toplama Yöntemi**

> • Kaynak: GitHub REST API v3 (api.github.com)
>
> • Araç: Python tabanlı otomatik veri çekimi (github_collector.py)
>
> • Dönem: Kasım 2024 – Ocak 2025
>
> • Kimlik doğrulama: GitHub Personal Access Token (5000 istek/saat)
>
> • Depolama: MySQL 8.0 veritabanı (github_analysis)
>
> • Toplam kayıt: 129 proje × 15 sütun

**3. Değişken Tanımları**

<table>
<colgroup>
<col style="width: 18%" />
<col style="width: 9%" />
<col style="width: 41%" />
<col style="width: 9%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Değişken</strong></th>
<th><strong>Veri Tipi</strong></th>
<th><strong>Açıklama</strong></th>
<th><strong>Yön</strong></th>
<th><strong>Örnek</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>id</p>
</blockquote></td>
<td><blockquote>
<p>Integer</p>
</blockquote></td>
<td><blockquote>
<p>Veritabanı birincil anahtar, otomatik artan</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>1, 2, 3</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>owner</p>
</blockquote></td>
<td><blockquote>
<p>String</p>
</blockquote></td>
<td><blockquote>
<p>Proje sahibi (GitHub kullanıcı/organizasyon adı)</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>facebook, google</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>repo_name</p>
</blockquote></td>
<td><blockquote>
<p>String</p>
</blockquote></td>
<td><blockquote>
<p>Proje adı (repository adı)</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>react, tensorflow</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>full_name</p>
</blockquote></td>
<td><blockquote>
<p>String</p>
</blockquote></td>
<td><blockquote>
<p>Tam proje yolu (owner/repo_name)</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>facebook/react</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>description</p>
</blockquote></td>
<td><blockquote>
<p>String</p>
</blockquote></td>
<td><blockquote>
<p>Projenin GitHub'daki kısa açıklaması</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>A JavaScript library for...</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>stars</p>
</blockquote></td>
<td><blockquote>
<p>Integer</p>
</blockquote></td>
<td><blockquote>
<p>Projeye verilen yıldız sayısı; topluluk onayını ve popülerliği yansıtır</p>
</blockquote></td>
<td><blockquote>
<p>Fayda ↑</p>
</blockquote></td>
<td><blockquote>
<p>240718</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>forks</p>
</blockquote></td>
<td><blockquote>
<p>Integer</p>
</blockquote></td>
<td><blockquote>
<p>Projenin çatallanma sayısı; pratik kullanım ve yeniden kullanılabilirlik göstergesi</p>
</blockquote></td>
<td><blockquote>
<p>Fayda ↑</p>
</blockquote></td>
<td><blockquote>
<p>49898</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>watchers</p>
</blockquote></td>
<td><blockquote>
<p>Integer</p>
</blockquote></td>
<td><blockquote>
<p>Projeyi izleyen (bildirim alan) kullanıcı sayısı; süregelen ilgiyi ölçer</p>
</blockquote></td>
<td><blockquote>
<p>Fayda ↑</p>
</blockquote></td>
<td><blockquote>
<p>240718</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>open_issues</p>
</blockquote></td>
<td><blockquote>
<p>Integer</p>
</blockquote></td>
<td><blockquote>
<p>Açık issue (sorun/istek) sayısı</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>1055</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>language</p>
</blockquote></td>
<td><blockquote>
<p>String</p>
</blockquote></td>
<td><blockquote>
<p>Projenin ana programlama dili</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>JavaScript, Python</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>created_at</p>
</blockquote></td>
<td><blockquote>
<p>DateTime</p>
</blockquote></td>
<td><blockquote>
<p>Projenin GitHub'da oluşturulma tarihi</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>2013-05-24 16:15:54</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>updated_at</p>
</blockquote></td>
<td><blockquote>
<p>DateTime</p>
</blockquote></td>
<td><blockquote>
<p>Projedeki son güncelleme tarihi</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>2025-11-20 00:38:27</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>collected_at</p>
</blockquote></td>
<td><blockquote>
<p>DateTime</p>
</blockquote></td>
<td><blockquote>
<p>Verinin API'den çekildiği tarih</p>
</blockquote></td>
<td><blockquote>
<p>—</p>
</blockquote></td>
<td><blockquote>
<p>2025-01-15</p>
</blockquote></td>
</tr>
</tbody>
</table>

**3.1. MCDM Analizinde Kullanılan Türetilmiş Değişkenler**

Veritabanından doğrudan çekilen ham değişkenlere ek olarak, analiz sırasında aşağıdaki değişkenler hesaplanmıştır:

<table>
<colgroup>
<col style="width: 22%" />
<col style="width: 29%" />
<col style="width: 38%" />
<col style="width: 9%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Değişken</strong></th>
<th><strong>Hesaplama</strong></th>
<th><strong>Açıklama</strong></th>
<th><strong>Yön</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>contributors</p>
</blockquote></td>
<td><blockquote>
<p>GitHub API (ayrı endpoint)</p>
</blockquote></td>
<td><blockquote>
<p>Projeye katkı sağlayan geliştirici sayısı; topluluk gücü</p>
</blockquote></td>
<td><blockquote>
<p>Fayda ↑</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>commits</p>
</blockquote></td>
<td><blockquote>
<p>GitHub API (commit_activity tablosu)</p>
</blockquote></td>
<td><blockquote>
<p>Toplam işleme sayısı; geliştirme aktivitesi yoğunluğu</p>
</blockquote></td>
<td><blockquote>
<p>Fayda ↑</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>güncellik</p>
</blockquote></td>
<td><blockquote>
<p>today - updated_at (gün)</p>
</blockquote></td>
<td><blockquote>
<p>Son güncelleme tarihinden itibaren geçen gün sayısı</p>
</blockquote></td>
<td><blockquote>
<p>Maliyet ↓</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>proje_yasi</p>
</blockquote></td>
<td><blockquote>
<p>today - created_at (gün)</p>
</blockquote></td>
<td><blockquote>
<p>Projenin oluşturulmasından itibaren geçen gün sayısı; olgunluk</p>
</blockquote></td>
<td><blockquote>
<p>Fayda ↑</p>
</blockquote></td>
</tr>
</tbody>
</table>

**3.2. ML Modelinde Kullanılan Türetilmiş Özellikler**

Makine öğrenmesi modeli için 7 ham kritere ek olarak 7 oransal özellik türetilmiştir:

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 29%" />
<col style="width: 45%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Özellik</strong></th>
<th><strong>Formül</strong></th>
<th><strong>Ne Ölçer</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><blockquote>
<p>Stars/Day</p>
</blockquote></td>
<td><blockquote>
<p>stars / proje_yasi</p>
</blockquote></td>
<td><blockquote>
<p>Günlük ortalama star kazanma hızı (büyüme trendi)</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Forks/Star</p>
</blockquote></td>
<td><blockquote>
<p>forks / stars</p>
</blockquote></td>
<td><blockquote>
<p>Star başına fork oranı (kullanılabilirlik)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Contributors/Fork</p>
</blockquote></td>
<td><blockquote>
<p>contributors / forks</p>
</blockquote></td>
<td><blockquote>
<p>Fork başına katkıcı yoğunluğu</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Commits/Contributor</p>
</blockquote></td>
<td><blockquote>
<p>commits / contributors</p>
</blockquote></td>
<td><blockquote>
<p>Katkıcı başına commit (bireysel verimlilik)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Commit Freshness</p>
</blockquote></td>
<td><blockquote>
<p>commits / güncellik</p>
</blockquote></td>
<td><blockquote>
<p>Güncelleme sıklığına göre commit yoğunluğu</p>
</blockquote></td>
</tr>
<tr class="even">
<td><blockquote>
<p>Watchers/Star</p>
</blockquote></td>
<td><blockquote>
<p>watchers / stars</p>
</blockquote></td>
<td><blockquote>
<p>Star başına izleyici oranı (gerçek ilgi)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td><blockquote>
<p>Age/Commits</p>
</blockquote></td>
<td><blockquote>
<p>proje_yasi / commits</p>
</blockquote></td>
<td><blockquote>
<p>Commit başına yaş (geliştirme hızı)</p>
</blockquote></td>
</tr>
</tbody>
</table>

**4. Kriter Yönleri ve Etki Dizisi**

MCDM analizinde 7 kriter kullanılmıştır. 6 tanesi **fayda kriteri** (yüksek değer = iyi), 1 tanesi **maliyet kriteri** (düşük değer = iyi) olarak tanımlanmıştır.

**Etki dizisi (impacts):** \[1, 1, 1, 1, -1, 1, 1\]

Sırasıyla: Stars (+), Forks (+), Contributors (+), Commits (+), Güncellik (−), Watchers (+), Proje Yaşı (+).

**5. Proje Kategorileri**

> • Web Frameworks (React, Vue, Angular, Flask, Django, Next.js vb.)
>
> • ML/AI (TensorFlow, PyTorch, Transformers, scikit-learn vb.)
>
> • DevOps (Docker, Kubernetes, Ansible, Terraform vb.)
>
> • Database (MongoDB, PostgreSQL, Redis, Elasticsearch vb.)
>
> • Security (OWASP, Metasploit, Vault vb.)
>
> • Mobile (Flutter, React Native, Ionic, Expo vb.)
>
> • Programming Languages (Rust, Go, TypeScript, Kotlin vb.)
>
> • Data Science (Pandas, Jupyter, Airflow, Spark vb.)
>
> • Cloud/Infrastructure (Nginx, Traefik, Consul vb.)

**6. Notlar ve Kısıtlar**

> • Tüm veriler GitHub API'nin anlık değerlerine dayanmaktadır; zaman serisi analizi yapılmamıştır.
>
> • Minimum 100 star filtresi uygulanmıştır.
>
> • Veri seti hem aktif projeler hem de terk edilmiş projeler hem de küratörlük listeleri (awesome-\*) içermektedir; bu çeşitlilik MCDM'nin farklı proje türlerini ayırt edip edemeyeceğini test etmek için bilinçli olarak korunmuştur.
>
> • GitHub API rate limit nedeniyle kimlik doğrulamalı erişim (5000 istek/saat) kullanılmıştır.
>
> • Bazı projelerde contributor verisi API limitasyonları nedeniyle yaklaşık değer içerebilir.

**Hazırlayan:** Furkan Deniz
