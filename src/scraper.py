"""
Turbo.az Scraper
Selenium istifadə edərək turbo.az-dan data çəkir.
"""

import asyncio
import logging
import os
import re
import time
import tempfile
from typing import Optional
from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger("turbo-az-scraper")

BASE_URL = "https://turbo.az"

# Full search params turbo.az expects (IDs for make/model, not names).
SEARCH_BASE_PARAMS = {
    "q[sort]": "",
    "q[make][]": "",
    "q[model][]": ["", ""],
    "q[used]": "",
    "q[region][]": "",
    "q[price_from]": "",
    "q[price_to]": "",
    "q[currency]": "azn",
    "q[loan]": "0",
    "q[barter]": "0",
    "q[category][]": "",
    "q[year_from]": "",
    "q[year_to]": "",
    "q[color][]": "",
    "q[fuel_type][]": "",
    "q[gear][]": "",
    "q[transmission][]": "",
    "q[engine_volume_from]": "",
    "q[engine_volume_to]": "",
    "q[power_from]": "",
    "q[power_to]": "",
    "q[mileage_from]": "",
    "q[mileage_to]": "",
    "q[only_shops]": "",
    "q[prior_owners_count][]": "",
    "q[seats_count][]": "",
    "q[market][]": "",
    "q[crashed]": "1",
    "q[painted]": "1",
    "q[for_spare_parts]": "0",
    "q[availability_status]": "",
}

# WSL/Linux: Chrome binary path. Set CHROME_BINARY or install chromium in WSL.
_CHROME_PATHS = (
    os.environ.get("CHROME_BINARY"),
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)


def _find_chrome_binary() -> Optional[str]:
    """Return first existing Chrome/Chromium binary path, or None."""
    for path in _CHROME_PATHS:
        if path and os.path.isfile(path):
            return path
    return None


class TurboAzScraper:
    """Turbo.az üçün Selenium əsaslı scraper."""
    
    def __init__(self):
        self.driver = None
    
    def _get_driver(self):
        """Selenium WebDriver yaradır və ya mövcud olanı qaytarır."""
        if self.driver is None:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--remote-debugging-pipe")
            options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            options.add_argument("--lang=az-AZ")
            binary = _find_chrome_binary()
            if binary:
                options.binary_location = binary
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
        
        return self.driver
    
    def _close_driver(self):
        """WebDriver-ı bağlayır."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _parse_tz_dropdown_options(self, driver, dropdown_id: str):
        """
        Parse (val, label) from tz-dropdown div (data-id=dropdown_id).
        Skips reset/not-found/hidden options.
        Returns:
            list of (data-val, label text).
        """
        out = []
        try:
            container = driver.find_element(By.CSS_SELECTOR, f'.tz-dropdown[data-id="{dropdown_id}"]')
            opts = container.find_elements(By.CSS_SELECTOR, ".tz-dropdown__list .tz-dropdown__option")
            for el in opts:
                val = (el.get_attribute("data-val") or "").strip()
                if not val:
                    continue
                cls = (el.get_attribute("class") or "")
                if "tz-dropdown__option--reset" in cls or "tz-dropdown__option--not-found" in cls or "is-hidden" in cls:
                    continue
                try:
                    label_el = el.find_element(By.CSS_SELECTOR, ".tz-dropdown__option-label .text")
                    label = (label_el.text or "").strip()
                except NoSuchElementException:
                    try:
                        label_el = el.find_element(By.CLASS_NAME, "tz-dropdown__option-label")
                        label = (label_el.text or "").strip()
                    except NoSuchElementException:
                        label = ""
                if label:
                    out.append((val, label))
        except NoSuchElementException:
            pass
        return out

    def _build_search_url(
        self,
        make_id: Optional[str] = None,
        model_id: Optional[str] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        fuel_id: Optional[int] = None,
        transmission_id: Optional[int] = None,
    ) -> str:
        """Axtarış URL-i qurur (turbo.az full format, make/model ID ilə)."""
        params = dict(SEARCH_BASE_PARAMS)
        if make_id:
            params["q[make][]"] = str(make_id)
        if model_id:
            params["q[model][]"] = ["", str(model_id)]
        if price_min is not None:
            params["q[price_from]"] = str(price_min)
        if price_max is not None:
            params["q[price_to]"] = str(price_max)
        if year_min is not None:
            params["q[year_from]"] = str(year_min)
        if year_max is not None:
            params["q[year_to]"] = str(year_max)
        if fuel_id is not None:
            params["q[fuel_type][]"] = str(fuel_id)
        if transmission_id is not None:
            params["q[transmission][]"] = str(transmission_id)
        return f"{BASE_URL}/autos?{urlencode(params, doseq=True)}"
    
    async def search_cars(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        limit: int = 20
    ) -> dict:
        """Avtomobil axtarışı aparır (make/model adından ID əldə edib full URL qurur)."""
        fuel_mapping = {
            "benzin": 1, "dizel": 2, "qaz": 3, "elektrik": 6, "hibrid": 7, "plug-in hibrid": 8,
        }
        transmission_mapping = {
            "mexaniki": 1, "avtomat": 2, "robot": 3, "variator": 4,
        }
        fuel_id = fuel_mapping.get((fuel_type or "").lower()) if fuel_type else None
        transmission_id = transmission_mapping.get((transmission or "").lower()) if transmission else None

        def _scrape():
            driver = self._get_driver()
            results = []
            make_id = None
            model_id = None
            try:
                if make:
                    driver.get(f"{BASE_URL}/autos")
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.tz-dropdown[data-id="q_make"]'))
                    )
                    time.sleep(0.3)
                    try:
                        driver.find_element(By.CSS_SELECTOR, '.tz-dropdown[data-id="q_make"] .tz-dropdown__selected').click()
                        time.sleep(0.2)
                    except Exception:
                        pass
                    make_opts = self._parse_tz_dropdown_options(driver, "q_make")
                    make_lower = make.strip().lower()
                    for val, label in make_opts:
                        txt = label.lower()
                        if txt == make_lower or txt.startswith(make_lower + " ") or txt.startswith(make_lower + "(") or make_lower in txt:
                            make_id = val
                            break
                    if not make_id:
                        all_makes = [label for _, label in make_opts[:20]]
                        logger.warning("Make not found. Sample options: %s", all_makes)
                        return {"success": False, "error": f"Marka tapılmadı: {make}"}
                    if model:
                        # Open make dropdown and click make option so model list is populated
                        try:
                            make_cont = driver.find_element(By.CSS_SELECTOR, '.tz-dropdown[data-id="q_make"]')
                            make_cont.find_element(By.CSS_SELECTOR, ".tz-dropdown__selected").click()
                            time.sleep(0.3)
                            opts_el = make_cont.find_elements(By.CSS_SELECTOR, ".tz-dropdown__list .tz-dropdown__option")
                            for el in opts_el:
                                if (el.get_attribute("data-val") or "").strip() == make_id:
                                    el.click()
                                    break
                            time.sleep(0.5)
                        except Exception:
                            pass
                        # Open model dropdown so options are in DOM
                        try:
                            driver.find_element(By.CSS_SELECTOR, '.tz-dropdown[data-id="q_model"] .tz-dropdown__selected').click()
                            time.sleep(0.2)
                        except Exception:
                            pass
                        model_opts = self._parse_tz_dropdown_options(driver, "q_model")
                        model_lower = model.strip().lower()
                        for val, label in model_opts:
                            txt = label.lower()
                            if txt == model_lower or txt.startswith(model_lower + " ") or txt.startswith(model_lower + "("):
                                model_id = val
                                break
                url = self._build_search_url(
                    make_id=make_id,
                    model_id=model_id,
                    price_min=price_min,
                    price_max=price_max,
                    year_min=year_min,
                    year_max=year_max,
                    fuel_id=fuel_id,
                    transmission_id=transmission_id,
                )
                logger.info(f"Searching: {url}")
                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "products-i"))
                )
                
                # Elanları tapırıq
                items = driver.find_elements(By.CLASS_NAME, "products-i")[:limit]
                
                for item in items:
                    try:
                        car = {}
                        
                        # Başlıq və link
                        link_elem = item.find_element(By.CLASS_NAME, "products-i__link")
                        car["url"] = link_elem.get_attribute("href")
                        car["id"] = car["url"].split("/")[-1].split("-")[0]
                        
                        # Şəkil
                        try:
                            img = item.find_element(By.CSS_SELECTOR, ".products-i__top img")
                            car["image"] = img.get_attribute("src")
                        except NoSuchElementException:
                            car["image"] = None
                        
                        # Başlıq (marka + model)
                        try:
                            title = item.find_element(By.CLASS_NAME, "products-i__name")
                            car["title"] = title.text.strip()
                        except NoSuchElementException:
                            car["title"] = "N/A"
                        
                        # Qiymət
                        try:
                            price = item.find_element(By.CLASS_NAME, "products-i__price")
                            car["price"] = price.text.strip()
                        except NoSuchElementException:
                            car["price"] = "N/A"
                        
                        # Əlavə məlumatlar (il, mühərrik, yürüş)
                        try:
                            attrs = item.find_elements(By.CLASS_NAME, "products-i__attributes")
                            if attrs:
                                attr_text = attrs[0].text.strip()
                                parts = [p.strip() for p in attr_text.split(",")]
                                if len(parts) >= 1:
                                    car["year"] = parts[0]
                                if len(parts) >= 2:
                                    car["engine"] = parts[1]
                                if len(parts) >= 3:
                                    car["mileage"] = parts[2]
                        except NoSuchElementException:
                            pass
                        
                        # Şəhər və tarix
                        try:
                            location = item.find_element(By.CLASS_NAME, "products-i__datetime")
                            loc_text = location.text.strip()
                            if "," in loc_text:
                                car["city"], car["date"] = [x.strip() for x in loc_text.split(",", 1)]
                            else:
                                car["city"] = loc_text
                        except NoSuchElementException:
                            pass
                        
                        results.append(car)
                        
                    except Exception as e:
                        logger.warning(f"Item parse error: {e}")
                        continue
                
                # Ümumi nəticə sayı
                try:
                    count_elem = driver.find_element(By.CLASS_NAME, "products-title__amount")
                    total_count = count_elem.text.strip()
                except NoSuchElementException:
                    try:
                        count_elem = driver.find_element(By.CLASS_NAME, "products-title__count")
                        total_count = count_elem.text.strip()
                    except NoSuchElementException:
                        total_count = str(len(results))
                
                return {
                    "success": True,
                    "total_count": total_count,
                    "returned_count": len(results),
                    "search_url": url,
                    "results": results
                }
                
            except TimeoutException:
                return {
                    "success": False,
                    "error": "Səhifə yüklənmədi (timeout)",
                    "search_url": url
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "search_url": url
                }
        
        # Sync funksiyasını async-də icra edirik
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _scrape)
    
    async def get_car_details(self, listing_id: str) -> dict:
        """Konkret elanın ətraflı məlumatlarını əldə edir."""
        
        # URL və ya ID ola bilər
        if listing_id.startswith("http"):
            url = listing_id
        else:
            url = f"{BASE_URL}/autos/{listing_id}"
        
        logger.info(f"Fetching details: {url}")
        
        def _scrape():
            driver = self._get_driver()
            
            try:
                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "product"))
                )
                
                details = {"url": url}
                
                # Başlıq
                try:
                    title = driver.find_element(By.CLASS_NAME, "product-title")
                    details["title"] = title.text.strip()
                except NoSuchElementException:
                    details["title"] = "N/A"
                
                # Qiymət (sidebar: product-price__i--bold)
                try:
                    price = driver.find_element(By.CSS_SELECTOR, ".product-price__i--bold")
                    details["price"] = price.text.strip()
                except NoSuchElementException:
                    try:
                        price = driver.find_element(By.CLASS_NAME, "product-price__i")
                        details["price"] = price.text.strip()
                    except NoSuchElementException:
                        details["price"] = "N/A"
                
                # Şəkillər (slider: product-photos__slider-top-i img)
                try:
                    images = driver.find_elements(By.CSS_SELECTOR, ".product-photos__slider-top-i img")
                    details["images"] = [img.get_attribute("src") for img in images if img.get_attribute("src")]
                except NoSuchElementException:
                    details["images"] = []
                
                # Xüsusiyyətlər
                details["specs"] = {}
                try:
                    props = driver.find_elements(By.CLASS_NAME, "product-properties__i")
                    for prop in props:
                        try:
                            label = prop.find_element(By.CLASS_NAME, "product-properties__i-name").text.strip()
                            value = prop.find_element(By.CLASS_NAME, "product-properties__i-value").text.strip()
                            details["specs"][label] = value
                        except NoSuchElementException:
                            continue
                except NoSuchElementException:
                    pass
                
                # Təsvir (product-description__content)
                try:
                    desc = driver.find_element(By.CLASS_NAME, "product-description__content")
                    details["description"] = desc.text.strip()
                except NoSuchElementException:
                    details["description"] = ""
                
                # Satıcı məlumatları (product-owner__info)
                try:
                    seller_name = driver.find_element(By.CLASS_NAME, "product-owner__info-name")
                    details["seller_name"] = seller_name.text.strip()
                except NoSuchElementException:
                    pass
                try:
                    region = driver.find_element(By.CLASS_NAME, "product-owner__info-region")
                    details["city"] = region.text.strip()
                except NoSuchElementException:
                    pass
                
                try:
                    phones = driver.find_elements(By.CSS_SELECTOR, ".product-phones__i a, .js-phones-hidden-block a")
                    details["phones"] = [p.text.strip() for p in phones if p.text.strip()]
                except NoSuchElementException:
                    details["phones"] = []
                
                # Statistika: Yeniləndi, Baxışların sayı (product-statistics__i)
                try:
                    stat_items = driver.find_elements(By.CSS_SELECTOR, ".product-statistics__i .product-statistics__i-text")
                    for s in stat_items:
                        t = s.text.strip()
                        if "Yeniləndi:" in t or "yeniləndi" in t.lower():
                            details["posted_date"] = t
                        elif "Baxışların" in t or "baxış" in t.lower():
                            details["views"] = t
                except NoSuchElementException:
                    pass
                
                return {"success": True, "details": details}
                
            except TimeoutException:
                return {"success": False, "error": "Səhifə yüklənmədi"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _scrape)
    
    async def get_makes_models(self, make: Optional[str] = None) -> dict:
        """Mövcud marka və modelləri əldə edir."""
        
        url = f"{BASE_URL}/autos"
        
        def _scrape():
            driver = self._get_driver()
            
            try:
                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.tz-dropdown[data-id="q_make"]'))
                )
                time.sleep(0.5)
                try:
                    driver.find_element(By.CSS_SELECTOR, '.tz-dropdown[data-id="q_make"] .tz-dropdown__selected').click()
                    time.sleep(0.4)
                except Exception:
                    pass
                if make:
                    make_opts = self._parse_tz_dropdown_options(driver, "q_make")
                    make_lower = make.strip().lower()
                    make_id = None
                    for val, label in make_opts:
                        if label.lower() == make_lower or make_lower in label.lower():
                            make_id = val
                            break
                    if not make_id:
                        return {"success": False, "error": f"Marka tapılmadı: {make}"}
                    try:
                        make_cont = driver.find_element(By.CSS_SELECTOR, '.tz-dropdown[data-id="q_make"]')
                        make_cont.find_element(By.CSS_SELECTOR, ".tz-dropdown__selected").click()
                        time.sleep(0.3)
                        for el in make_cont.find_elements(By.CSS_SELECTOR, ".tz-dropdown__list .tz-dropdown__option"):
                            if (el.get_attribute("data-val") or "").strip() == make_id:
                                el.click()
                                break
                        time.sleep(0.5)
                    except Exception:
                        pass
                    model_opts = self._parse_tz_dropdown_options(driver, "q_model")
                    models = [label for _, label in model_opts]
                    return {"success": True, "make": make, "models": models}
                
                make_opts = self._parse_tz_dropdown_options(driver, "q_make")
                makes = [label for _, label in make_opts]
                return {"success": True, "makes": makes}
                
            except TimeoutException:
                return {"success": False, "error": "Səhifə yüklənmədi"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _scrape)
    
    async def get_trending(self, category: str = "new", limit: int = 20) -> dict:
        """Ən yeni/populyar elanları əldə edir."""
        
        if category == "vip":
            url = f"{BASE_URL}/autos?q[extras][]=vip"
        elif category == "popular":
            url = f"{BASE_URL}/autos?order=view_count"
        else:  # new
            url = f"{BASE_URL}/autos"
        
        # search_cars funksiyasından istifadə edirik
        return await self.search_cars(limit=limit)
    
    def __del__(self):
        """Destructor - driver-ı bağlayır."""
        self._close_driver()
