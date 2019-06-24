from ligmos.utils import amq, classes, database, confparsers


def checkAMQConnections(amqbrokers, subscribe=True):
    """
    This is intended to be inside of some loop structure.
    It's primarily used for checking whether the connection to the ActiveMQ
    broker is still valid, and, if it was killed (set to None) because the
    heartbeat failed, attempt to both reconnect and resubscribe to the
    topics.
    """
    for bconn in amqbrokers:
        # From above, amqbrokers is a dict with values that are a list of
        #   connection object, list of topics, listener object
        connChecking = amqbrokers[bconn][0]
        thisListener = amqbrokers[bconn][1]
        if connChecking.conn is None:
            print("No connection at all! Retrying...")
            # The topics were already stuffed into the connChecking object,
            #   but it's nice to remember that we're subscribing to them
            connChecking.connect(listener=thisListener, subscribe=subscribe)
        elif connChecking.conn.transport.connected is False:
            print("Connection died! Reestablishing...")
            connChecking.connect(listener=thisListener, subscribe=subscribe)
        else:
            print("Connection still valid")

        # Make sure we save any connection changes and give it back
        amqbrokers[bconn] = [connChecking, thisListener]

    return amqbrokers


def establishAMQIDBConnections(comm):
    """
    Set up the actual connections, which we'll then give back to the actual
    objects for them to do stuff with afterwards
    """
    amqbrokers = {}
    influxdatabases = {}

    for commsection in comm:
        # Rename for easier access/passing
        cobj = comm[commsection]

        # Now check the properties of this object to see if it's something we
        #   actually regconize and then connect to
        if cobj.type.lower() == 'activemq':
            # We get brokerlistener back as a return just in case it was
            #   None initially, in which case amq.setupBroker would give one
            conn, amqlistener = amq.setupAMQBroker(cobj,
                                                   amqtopics[commsection],
                                                   listener=amqlistener)

            # Store this so we can check/use it later
            brokerbits = [conn, amqlistener]
            amqbrokers.update({commsection: brokerbits})
        elif cobj.type.lower() == 'influxdb':
            # Create an influxdb object that can be spread around to
            #   connect and commit packets when they're created.
            #   Leave it disconnected initially.
            idb = database.influxobj(database=None,
                                     host=cobj.host,
                                     port=cobj.port,
                                     user=cobj.user,
                                     pw=cobj.password,
                                     connect=False)

            # Connect briefly to check/verify everything is working
            idb.connect()
            idb.disconnect()

            # Store this so we can check/use it later
            influxdatabases.update({commsection: idb})
        else:
            # No other types are defined yet
            pass

    return amqbrokers, influxdatabases


def getAllAMQTopics(config):
    """
    Since we can have multiple connections to a single broker or database or
    whatever, we need to search through all of our defined sections to
    pull out some of the specifics into one place; that makes our
    connection/reconnection/subscription logic way easier
    """
    amqtopics = {}
    for sect in config:
        csObj = config[sect]
        try:
            brokerTag = csObj.broker
            brokertype = comm[brokerTag].type
        except AttributeError:
            # If we end up in here, we're completely hoopajooped so give up
            break

        if brokertype.lower() == 'activemq':
            # Gather up broker stuff
            try:
                # First see if we have anything previously gathered, to make
                #   sure we don't accidentally clobber anything
                alltopics = amqtopics[brokerTag]
            except KeyError:
                alltopics = []

            # Get the topics; it's guaranteed to be a list
            thesetopics = amq.gatherAMQTopics(csObj)
            alltopics += thesetopics

            # list(set()) to quickly take care of any dupes
            amqtopics.update({brokerTag: list(set(alltopics))})

    return amqtopics


cfile = './alfred.conf'
confclass = classes.hostTarget
pfile = './passwords.conf'

# cfile = './abu.conf'
# confclass = classes.sneakyTarget
# pfile = './passwords.conf'

# Parse the things!
config, comm = confparsers.parseConfig(cfile, confclass,
                                       passfile=pfile,
                                       searchCommon=True,
                                       enableCheck=True,
                                       debug=True)

# Check to see if there are any connections/objects to establish
amqlistener = amq.silentSubscriber()

# NOTE: The idea is that basically ALL of what follows will become completely
#   generic boilerplate, to be shuffled away behind the scenes somewhere
#   for much easier access.  The only thing that might poke out is the stuff
#   above, but even that can be hidden away if we really need/want to do that.

amqtopics = getAllAMQTopics(config)
amqbrokers, influxdatabases = establishAMQIDBConnections(comm)

# This part should be in whatever loop gets set up to continually run
#   amqbroker sections containing the connection objects can change, so
#   make sure that we get it back in case a change (reconnection) happened.
amqbrokers = checkAMQConnections(amqbrokers, subscribe=False)
