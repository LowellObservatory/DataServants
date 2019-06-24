from ligmos.utils import amq, classes, database, confparsers


def establishAMQIDBConnections(comm):
    """
    Set up the actual connections, which we'll then give back to the actual
    objects for them to do stuff with afterwards.
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

amqtopics = amq.getAllTopics(config, comm)
amqbrokers, influxdatabases = establishAMQIDBConnections(comm)

# This part should be in whatever loop gets set up to continually run
#   amqbroker sections containing the connection objects can change, so
#   make sure that we get it back in case a change (reconnection) happened.
amqbrokers = amq.checkConnections(amqbrokers, subscribe=False)
