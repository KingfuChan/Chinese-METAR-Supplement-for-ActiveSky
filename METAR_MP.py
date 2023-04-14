import multiprocessing
import METAR_proxy
import METAR_server


if __name__ == '__main__':
    CONCERNED = input("请输入特别关注机场，以空格分隔>").split()
    # Create two processes for each job
    p1 = multiprocessing.Process(target=METAR_proxy.main)
    p2 = multiprocessing.Process(target=METAR_server.main, args=[CONCERNED])

    # Start both processes
    p1.start()
    p2.start()

    # Wait for both processes to finish
    try:
        p1.join()
        p2.join()
    except KeyboardInterrupt:
        p1.terminate()
        p2.terminate()
