import uvicorn
from asyncio import run
from time import sleep
from multiprocessing import Process, Queue
from engine.linkedin_scraper import LinkedInScraper
from engine.cleaner import Cleaner


def server() -> None:
    uvicorn.run("app:app", port=8000)


def scraper(queue: Queue) -> None:
    run(
        LinkedInScraper(
            "https://www.linkedin.com/jobs/search/?&keywords=software%20engineer", queue
        ).init()
    )


def cleaner(queue: Queue) -> None:
    run(Cleaner(queue).run())


def main() -> None:
    clean_queue = Queue()

    process_kwargs = (
        {"target": server, "args": (), "name": "server"},
        {"target": scraper, "args": (clean_queue,), "name": "scraper"},
        {"target": cleaner, "args": (clean_queue,), "name": "cleaner"},
    )

    processes = [Process(**kwargs) for kwargs in process_kwargs]

    for process in processes:
        process.start()

    try:
        for i in range(len(processes)):
            processes[i].join()

            if not processes[i].is_alive():
                print(f"[main] {process_kwargs[i]['name']} has shut down")
                process.kill()
                processes[i] = Process(**process_kwargs[i])
                processes[i].start()
                print(f"[main] Restarted {process_kwargs[i]['name']}")

        sleep(1)
    except BaseException:
        print("[main] Shutting down...")

        for i in range(len(processes)):
            print(f"[main] Shutting down {process_kwargs[i]['name']}")
            processes[i].terminate()
            processes[i].join()
            print(f"[main] {process_kwargs[i]['name']} has shut down")

        print("[main] All processes have shut down")


if __name__ == "__main__":
    main()
