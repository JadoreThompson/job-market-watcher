import uvicorn
from asyncio import run
from time import sleep
from multiprocessing import Process
from engine.scraper import Scraper


def server() -> None:
    uvicorn.run("app:app", port=8000)


def engine() -> None:
    run(
        Scraper(
            "https://www.linkedin.com/jobs/search/?&keywords=software%20engineer"
        ).init()
    )


def main() -> None:
    process_kwargs = (
        {"target": server, "args": (), "name": "server"},
        {"target": engine, "args": (), "name": "engine"},
    )

    processes = [Process(**kwargs) for kwargs in process_kwargs]

    for process in processes:
        process.start()

    try:
        for i in range(len(processes)):
            processes[i].join()

            if not processes[i].is_alive():
                processes[i] = Process(**process_kwargs[i])
                processes[i].start()

        sleep(1)
    except BaseException:
        print("[main] Shutting down...")

        for process in processes:
            process.join()
            process.terminate()


if __name__ == "__main__":
    main()
