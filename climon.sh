case "$1" in
    start)
        python3 mon.py start
        python3 web.py start
        ;;
    stop)
        python3 mon.py stop
        python3 web.py stop
        ;;
    restart)
        python3 mon.py restart
        python3 web.py restart
        ;;
    *)
        echo "Usage: $SCRIPTNAME {start|stop|restart}" >&2
        exit 3
        ;;
esac

exit 0
