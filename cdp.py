import requests
import threading
from termcolor import colored
from datetime import datetime
import os, sys
from time import sleep
import time
import random


def clear():
    os.system("cls") if os.name == "nt" else os.system("clear")


def show_banner():
    colors = ["red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    banner = """
 ██████╗ ██████╗ ██████╗     ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗
██╔═══██╗██╔══██╗██╔══██╗    ██╔══██╗██╔══██╗██╔═══██╗██║ ██╔╝██║   ██║
██║   ██║██████╔╝██║  ██║    ██████╔╝██████╔╝██║   ██║█████╔╝ ██║   ██║
██║   ██║██╔═══╝ ██║  ██║    ██╔═══╝ ██╔═══╝ ██║   ██║██╔═██╗ ██║   ██║
╚██████╔╝██║     ██████╔╝    ██║     ██║     ╚██████╔╝██║  ██╗╚██████╔╝
 ╚═════╝ ╚═╝     ╚═════╝     ╚═╝     ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ 
                      CDP PROXY V1.00.1
    """
    for _ in range(5):  # Lặp lại 5 lần
        clear()
        color = random.choice(colors)  # Chọn màu ngẫu nhiên
        print(colored(banner, color, attrs=["bold"]))
        time.sleep(0.5)  # Dừng 0.5 giây giữa mỗi lần hiển thị


class ProxyInfo:
    def __init__(self, proxy):
        self.proxy = proxy
        self.location = None
        self.type = None
        self.response_time = None
        self.ssl_supported = None  # Thêm trạng thái hỗ trợ SSL
        self.tls_supported = None  # Thêm trạng thái hỗ trợ TLS

    def determine_location(self):
        try:
            response = requests.get('https://ipinfo.io/json', proxies={"http": self.proxy, "https": self.proxy}, timeout=1)
            self.location = response.json().get("city", "Unknown")
            return True
        except:
            self.location = "Unknown"
            return False

    def determine_type(self):
        self.type = "Unknown"
        for t in ["http", "https"]:
            try:
                response = requests.get(f"http://www.google.com", proxies={t: self.proxy}, timeout=1)
                if response.status_code == 200:
                    self.type = t.upper()
                    return
            except:
                continue

    def measure_response_time(self):
        try:
            response = requests.get("http://www.google.com", proxies={"http": self.proxy, "https": self.proxy}, timeout=1)
            self.response_time = response.elapsed.total_seconds()
        except:
            self.response_time = float('inf')

    def check_ssl_support(self):
        """Kiểm tra proxy có hỗ trợ SSL hay không"""
        try:
            response = requests.get("https://www.google.com", proxies={"https": self.proxy}, timeout=1)
            self.ssl_supported = response.status_code == 200
        except:
            self.ssl_supported = False

    def check_tls_support(self):
        """Kiểm tra proxy có hỗ trợ TLS hay không (thực chất kiểm tra HTTPS)"""
        try:
            response = requests.get("https://www.google.com", proxies={"https": self.proxy}, timeout=1)
            # Kiểm tra xem có kết nối HTTPS thành công hay không
            if response.status_code == 200:
                self.tls_supported = True
            else:
                self.tls_supported = False
        except:
            self.tls_supported = False

    def get_info(self):
        is_live = self.determine_location()
        if is_live:
            self.determine_type()
            self.measure_response_time()
            self.check_ssl_support()  # Gọi kiểm tra SSL
            self.check_tls_support()  # Gọi kiểm tra TLS
        return is_live


def delete_existing_files():
    result_folder = "result"
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)  # Tạo thư mục result nếu chưa có

    # Xóa tất cả các file cũ trong thư mục result
    for filename in os.listdir(result_folder):
        file_path = os.path.join(result_folder, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(colored(f"[INFO] Đã xóa file cũ: {file_path}", "yellow"))


def filter_duplicates(filename):
    """Lọc trùng các proxy trong file và trả về danh sách proxy duy nhất"""
    with open(filename, "r") as file:
        proxies = file.readlines()

    # Loại bỏ các proxy trùng lặp
    unique_proxies = list(set(proxy.strip() for proxy in proxies))
    print(f"[INFO] Đã lọc {len(proxies) - len(unique_proxies)} proxy trùng lặp.")
    
    return unique_proxies


def check_live_proxies(filename, num_threads, num_rounds):
    delete_existing_files()

    def perform_check(round_number):
        live_proxies = {
            "HTTP": [],
            "HTTPS": [],
            "HTTP_SSL": [],
            "HTTPS_SSL": [],
            "ALL_SSL": [],
            "ALL_TLS": [],  # Thêm nhóm proxy hỗ trợ TLS
        }

        # Lọc trùng trước khi kiểm tra
        unique_proxies = filter_duplicates(filename)

        threads = []
        for proxy in unique_proxies:
            thread = threading.Thread(target=check_proxy_thread, args=(proxy, live_proxies))
            thread.start()
            threads.append(thread)

            if len(threads) >= num_threads:
                for thread in threads:
                    thread.join()
                threads = []

        for thread in threads:
            thread.join()

        # Lưu kết quả vào các tệp trong thư mục 'result'
        result_folder = "result"

        with open(os.path.join(result_folder, f"round_{round_number}_http.txt"), "w") as file:
            for proxy in live_proxies["HTTP"]:
                file.write(proxy + "\n")

        with open(os.path.join(result_folder, f"round_{round_number}_https.txt"), "w") as file:
            for proxy in live_proxies["HTTPS"]:
                file.write(proxy + "\n")

        with open(os.path.join(result_folder, f"round_{round_number}_http_ssl_supported.txt"), "w") as file:
            for proxy in live_proxies["HTTP_SSL"]:
                file.write(proxy + "\n")

        with open(os.path.join(result_folder, f"round_{round_number}_https_ssl_supported.txt"), "w") as file:
            for proxy in live_proxies["HTTPS_SSL"]:
                file.write(proxy + "\n")

        with open(os.path.join(result_folder, f"round_{round_number}_all_ssl_supported.txt"), "w") as file:
            for proxy in live_proxies["ALL_SSL"]:
                file.write(proxy + "\n")

        with open(os.path.join(result_folder, f"round_{round_number}_all_tls_supported.txt"), "w") as file:
            for proxy in live_proxies["ALL_TLS"]:
                file.write(proxy + "\n")

        with open(os.path.join(result_folder, f"round_{round_number}_result.txt"), "w") as file:
            all_proxies = live_proxies["HTTP"] + live_proxies["HTTPS"] + live_proxies["HTTP_SSL"] + \
                          live_proxies["HTTPS_SSL"] + live_proxies["ALL_SSL"] + live_proxies["ALL_TLS"]
            for proxy in all_proxies:
                file.write(proxy + "\n")

        # Liệt kê số lượng
        print(f"Số lượng proxy HTTP (vòng {round_number}): {len(live_proxies['HTTP'])}")
        print(f"Số lượng proxy HTTPS (vòng {round_number}): {len(live_proxies['HTTPS'])}")
        print(f"Số lượng proxy HTTP hỗ trợ SSL (vòng {round_number}): {len(live_proxies['HTTP_SSL'])}")
        print(f"Số lượng proxy HTTPS hỗ trợ SSL (vòng {round_number}): {len(live_proxies['HTTPS_SSL'])}")
        print(f"Số lượng proxy tất cả hỗ trợ SSL (HTTP + HTTPS) (vòng {round_number}): {len(live_proxies['ALL_SSL'])}")
        print(f"Số lượng proxy hỗ trợ TLS (vòng {round_number}): {len(live_proxies['ALL_TLS'])}")
        print(f"Tổng số proxy sống (vòng {round_number}): {sum(len(v) for v in live_proxies.values())}")

    # Thực hiện kiểm tra qua nhiều vòng
    for round_number in range(1, num_rounds + 1):
        print(colored(f"Bắt đầu kiểm tra vòng {round_number}", "yellow", attrs=["bold"]))
        perform_check(round_number)
        print(colored(f"ROUND {round_number} END", "yellow", attrs=["bold"]))


def check_proxy_thread(proxy, live_proxies):
    proxy_info = ProxyInfo(proxy)
    if proxy_info.get_info():
        info_display = f"Proxy: {proxy_info.proxy} | Type: {proxy_info.type} | Response Time: {proxy_info.response_time * 1000:.2f}ms"
        if proxy_info.ssl_supported:
            info_display += " | SSL: Supported"
        else:
            info_display += " | SSL: Not Supported"

        if proxy_info.tls_supported:
            info_display += " | TLS: Supported"
        else:
            info_display += " | TLS: Not Supported"

        info_display += f" | Location: {proxy_info.location}"

        # Hiển thị thông tin proxy live
        print(colored(info_display, "green"))

        # Lưu proxy vào danh sách phù hợp
        if proxy_info.type == "HTTP":
            live_proxies["HTTP"].append(proxy_info.proxy)
            if proxy_info.ssl_supported:
                live_proxies["HTTP_SSL"].append(proxy_info.proxy)
                live_proxies["ALL_SSL"].append(proxy_info.proxy)
            if proxy_info.tls_supported:
                live_proxies["ALL_TLS"].append(proxy_info.proxy)

        if proxy_info.type == "HTTPS":
            live_proxies["HTTPS"].append(proxy_info.proxy)
            if proxy_info.ssl_supported:
                live_proxies["HTTPS_SSL"].append(proxy_info.proxy)
                live_proxies["ALL_SSL"].append(proxy_info.proxy)
            if proxy_info.tls_supported:
                live_proxies["ALL_TLS"].append(proxy_info.proxy)
    # Không làm gì nếu proxy chết

def main():
    show_banner()

    input_file = input("Nhập tên file proxy (có định dạng .txt): ")
    while not os.path.isfile(input_file):
        print(colored(f"[ERROR] Không tìm thấy file {input_file}. Hãy thử lại.", "red"))
        input_file = input("Nhập lại tên file proxy: ")

    num_threads = int(input("Nhập số lượng thread kiểm tra proxy: "))
    num_rounds = int(input("Nhập số vòng kiểm tra: "))
    check_live_proxies(input_file, num_threads, num_rounds)


if __name__ == "__main__":
    main()
