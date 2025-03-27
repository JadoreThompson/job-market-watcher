import uvicorn
import time
import asyncio

from multiprocessing import Process, Queue
from engine.chart_generator import ChartGenerator
from engine.linkedin_scraper import LinkedInScraper
from engine.cleaner import Cleaner


def server() -> None:
    uvicorn.run("app:app", port=8000)


def scraper(queue: Queue) -> None:
    asyncio.run(
        LinkedInScraper(
            "https://www.linkedin.com/jobs/search/?&keywords=software%20engineer", queue
        ).init()
    )


def cleaner(queue: Queue) -> None:
    asyncio.run(Cleaner(queue).run())


def chart_generator() -> None:
    asyncio.run(ChartGenerator().run())


def main() -> None:
    clean_queue = Queue()

    process_kwargs = (
        {"target": server, "args": (), "name": "server"},
        {"target": scraper, "args": (clean_queue,), "name": "scraper"},
        {"target": cleaner, "args": (clean_queue,), "name": "cleaner"},
        {"target": chart_generator, "args": (), "name": "chart_generator"},
    )

    processes = [Process(**kwargs) for kwargs in process_kwargs]

    for process in processes:
        process.start()

    try:
        while True:
            for i in range(len(processes)):
                if not processes[i].is_alive():
                    print(
                        f"[main] {process_kwargs[i]['name']} PID: {processes[i].pid} has shut down"
                    )
                    processes[i].kill()
                    processes[i].join()
                    processes[i] = Process(**process_kwargs[i])
                    processes[i].start()
                    print(f"[main] Restarted {process_kwargs[i]['name']}")
            time.sleep(5)
    except BaseException:
        print("[main] Shutting down...")

        for i in range(len(processes)):
            print(
                f"[main] Shutting down {process_kwargs[i]['name']} PID: {processes[i].pid}"
            )
            processes[i].terminate()
            processes[i].join()
            print(f"[main] {process_kwargs[i]['name']} has shut down")

        print("[main] All processes have shut down")


if __name__ == "__main__":
    main()
