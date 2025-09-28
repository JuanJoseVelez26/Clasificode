import os
import time
import json
from typing import Iterator, Dict, Any, Optional, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DianiScraper:
    """
    Scraper Selenium (headless) para resoluciones de la DIAN.
    Variables de entorno:
      - DIAN_BASE_URL (obligatorio)
      - SELENIUM_DRIVER_PATH (ruta al chromedriver)
      - SCRAPER_TIMEOUT_S (segundos, por defecto 20)
    """

    def __init__(self):
        # URL por defecto: página de resoluciones de clasificación arancelaria
        self.base_url = os.getenv('DIAN_BASE_URL') or 'https://www.dian.gov.co/normatividad/Paginas/ResoClasifiAracelaria.aspx'
        self.driver_path = os.getenv('SELENIUM_DRIVER_PATH')
        self.timeout = int(os.getenv('SCRAPER_TIMEOUT_S') or '20')
        self._driver = None

    def _log(self, level: str, msg: str, **kv):
        rec = {"ts": int(time.time()), "level": level, "msg": msg}
        if kv:
            rec.update(kv)
        print(json.dumps(rec, ensure_ascii=False))

    def _init_driver(self):
        if self._driver is not None:
            return
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        if self.driver_path:
            self._driver = webdriver.Chrome(self.driver_path, options=options)
        else:
            self._driver = webdriver.Chrome(options=options)

    def close(self):
        try:
            if self._driver:
                self._driver.quit()
        finally:
            self._driver = None

    def iter_resolutions(self) -> Iterator[Dict[str, Any]]:
        """
        Itera sobre el listado de resoluciones y devuelve dicts:
        { 'url': str, 'title': str, 'date': str, 'type': 'RESOLUCION'|'NOTA'|... }
        """
        self._init_driver()
        driver = self._driver
        self._log('info', 'opening_base_url', url=self.base_url)
        driver.get(self.base_url)

        # Heurísticos para SharePoint/DIAN: capturar anchors relevantes del contenido principal
        anchors: List[Any] = []
        try:
            # Esperar a que el DOM tenga anchors
            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a'))
            )
            # 1) PDFs directos
            anchors.extend(driver.find_elements(By.CSS_SELECTOR, 'a[href*=".pdf" i]'))
            # 2) Enlaces con palabras clave típicas
            anchors.extend(driver.find_elements(By.XPATH, "//a[contains(translate(text(),'RESOLUCIÓN','resolución'),'resoluci') or contains(translate(text(),'CLASIFICACIÓN','clasificación'),'clasific')]"))
            # 3) Dentro del contenedor principal (cuando existe)
            try:
                main = driver.find_element(By.CSS_SELECTOR, 'main')
                anchors.extend(main.find_elements(By.CSS_SELECTOR, 'a'))
            except Exception:
                pass
        except Exception as e:
            self._log('warn', 'no_anchors_found', error=str(e))

        # De-duplicar por href
        seen = set()
        def _extract_date_from_text(t: str) -> str:
            import re
            m = re.search(r"(\d{2}[\/-]\d{2}[\/-]\d{4}|\d{4})", t)
            return m.group(1) if m else ''

        for a in anchors:
            try:
                url = (a.get_attribute('href') or '').strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                title = (a.text or '').strip()
                if not title:
                    # Usa parte final del href como título básico
                    title = url.rsplit('/', 1)[-1]
                date = _extract_date_from_text(title)
                rtype = 'RESOLUCION'
                # Filtrar enlaces irrelevantes (correo, javascript, menús)
                if url.startswith('mailto:') or url.startswith('javascript:'):
                    continue
                yield {
                    'url': url,
                    'title': title,
                    'date': date,
                    'type': rtype,
                }
            except Exception as e:
                self._log('error', 'link_parse_error', error=str(e))
                continue

    def fetch_page(self, url: str) -> Dict[str, Any]:
        """Devuelve {'content_type':'html'|'pdf', 'content':bytes|str}.
        Si es PDF, descarga bytes; si es HTML, devuelve outerHTML.
        """
        self._init_driver()
        driver = self._driver
        self._log('info', 'fetch_url', url=url)
        driver.get(url)
        time.sleep(1)
        # Heurística: si hay <embed> o <object> PDF, intentamos obtener el src
        try:
            embeds = driver.find_elements(By.CSS_SELECTOR, 'embed, object')
            for emb in embeds:
                src = emb.get_attribute('src') or ''
                if '.pdf' in src.lower():
                    # Descargar bytes via navegador no es directo; aquí sólo reportamos la URL
                    # Ingestor puede usar requests para descargar el PDF si es necesario
                    return { 'content_type': 'pdf', 'content': src }
        except Exception:
            pass
        # HTML
        html = driver.page_source
        return { 'content_type': 'html', 'content': html }
