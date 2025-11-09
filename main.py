import time
import json
import re
import argparse
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

def scrape_spotify_playlist(playlist_url):
    """
    Сканує плейлист Spotify, використовуючи undetected-chromedriver для обходу захисту.

    Args:
        playlist_url (str): URL-адреса плейлиста Spotify.

    Returns:
        dict: Словник з інформацією про треки, або None у разі помилки.
    """
    
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")

    # Ініціалізуємо драйвер без вказання версії,
    # щоб бібліотека визначила її автоматично.
    try:
        print("Автоматичне налаштування chromedriver...")
        driver = uc.Chrome(options=options) 
    except Exception as e:
        print(f"Помилка під час ініціалізації драйвера: {e}")
        print("Це може статися під час першого запуску, коли завантажується драйвер.")
        print("Спробуйте запустити скрипт ще раз.")
        return None

    try:
        print(f"Відкриваю URL: {playlist_url}")
        driver.get(playlist_url)
        time.sleep(10)

        print("Прокручую сторінку для завантаження всіх треків...")
        
        last_height = driver.execute_script("return document.body.scrollHeight")

        for i in range(10):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Досягнуто кінця сторінки.")
                break
            last_height = new_height
            print(f"Прокрутка {i+1}...")
        
        print("Завантаження завершено. Починаю аналіз сторінки...")
        page_source = driver.page_source
        
        if "Unsupported browser" in page_source or "To play this content, you'll need the Spotify app" in page_source:
            print("ПОМИЛКА: Spotify заблокував доступ.")
            with open('spotify_page_source_blocked.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print("HTML-код сторінки збережено у файл 'spotify_page_source_blocked.html'")
            return None

        soup = BeautifulSoup(page_source, 'html.parser')
        tracks_data = {"tracks": []}
        track_rows = soup.find_all('div', attrs={'data-testid': 'tracklist-row'})
        
        print(f"Знайдено {len(track_rows)} рядків для аналізу.")
        if not track_rows:
            with open('spotify_page_source_debug.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print("Не знайдено рядків з треками. HTML-код збережено у 'spotify_page_source_debug.html'.")

        for row in track_rows:
            links = row.find_all('a', href=True)
            
            track_name = "Невідома назва"
            spotify_url = "URL не знайдено"
            artist_names = []

            for link in links:
                href = link['href']
                if '/track/' in href:
                    inner_div = link.find('div')
                    track_name = inner_div.text.strip() if inner_div else link.text.strip()
                    spotify_url = 'https://open.spotify.com' + href
                elif '/artist/' in href:
                    artist_names.append(link.text.strip())
            
            if spotify_url != "URL не знайдено":
                artist = ', '.join(artist_names) if artist_names else 'Невідомий виконавець'
                tracks_data["tracks"].append({
                    "name": track_name,
                    "artist": artist,
                    "spotify_url": spotify_url
                })
        
        return tracks_data

    except Exception as e:
        print(f"Сталася непередбачена помилка: {e}")
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сканер для плейлистів Spotify.")
    parser.add_argument("-url", "--url", required=True, help="Повне посилання на плейлист Spotify.")
    args = parser.parse_args()
    
    playlist_url = args.url
    print(f"Починаю сканування плейлиста: {playlist_url}")
    scraped_data = scrape_spotify_playlist(playlist_url)

    if scraped_data and scraped_data["tracks"]:
        print(f"\n--- Успішно знайдено {len(scraped_data['tracks'])} треків ---")
        print(json.dumps(scraped_data, indent=2, ensure_ascii=False))

        output_filename = 'spotify_playlist.json'
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        print(f"\nДані успішно збережено у файл '{output_filename}'")
    else:
        print("\nНе вдалося знайти треки. Перевірте посилання або спробуйте запустити скрипт ще раз.")