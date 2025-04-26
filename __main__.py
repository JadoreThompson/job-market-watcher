import asyncio
import time
import uvicorn

from multiprocessing import Process, Queue
from engine.chart_generator import ChartGenerator
from engine.scrapers import GoogleJobsScraper, LinkedInScraper
from engine.cleaner import Cleaner


def run_server() -> None:
    uvicorn.run("app:app", port=8000)


def run_scraper(queue: Queue) -> None:
    asyncio.run(
        GoogleJobsScraper(
            "https://www.google.com/search?q=software%20engineer%20internship&oq=software%20engineer%20internship%20&gs_lcrp=EgZjaHJvbWUqBggAEEUYOzIGCAAQRRg7MgYIARBFGDsyBwgCEAAYgAQyBwgDEAAYgAQyBggEEEUYQTIGCAUQRRg8MgYIBhBFGEEyBggHEC4YQNIBCDYwNjRqMGoxqAIIsAIB8QX4SipSyeWHlg&sourceid=chrome&ie=UTF-8&jbr=sep:0&udm=8&ved=2ahUKEwi_4-C6u_SMAxV3zwIHHdJJGO8Q3L8LegQIIxAN#vhid=vt%3D20/docid%3DSCXfdu4XPPzq7xj9AAAAAA%3D%3D&vssid=jobs-detail-viewer",
            queue,
        ).run()
    )


def run_cleaner(queue: Queue) -> None:
    asyncio.run(Cleaner(queue).run())


def run_chart_generator() -> None:
    asyncio.run(ChartGenerator().run())


def main() -> None:
    queue = Queue()

    process_kwargs = (
        # {"target": run_server, "args": (), "name": "server"},
        {"target": run_scraper, "args": (queue,), "name": "scraper"},
        {"target": run_cleaner, "args": (queue,), "name": "cleaner"},
        # {"target": run_chart_generator, "args": (), "name": "chart_generator"},
    )

    processes = [Process(**kwargs) for kwargs in process_kwargs]

    for process in processes:
        process.start()

    try:
        while True:
            for i in range(len(processes)):
                if not processes[i].is_alive():
                    print(
                        f"[main] Name: {process_kwargs[i]['name']} PID: {processes[i].pid} has shut down"
                    )
                    processes[i].kill()
                    processes[i].join()
                    processes[i] = Process(**process_kwargs[i])
                    processes[i].start()
                    print(f"[main] Restarted {process_kwargs[i]['name']}")
            time.sleep(1)
    except BaseException:
        print("[main] Shutting down...")

        for i in range(len(processes)):
            print(
                f"[main] Shutting down Name: {process_kwargs[i]['name']} PID: {processes[i].pid}"
            )
            processes[i].terminate()
            processes[i].join()
            print(f"[main] {process_kwargs[i]['name']} has shut down")

        print("[main] All processes have shut down")


if __name__ == "__main__":
    main()
