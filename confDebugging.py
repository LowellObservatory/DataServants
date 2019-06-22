from ligmos.utils import amq, classes, database, confutils, confparsers

# cfile = './alfred.conf'
# confclass = classes.hostTarget
# pfile = './passwords.conf'

cfile = './abu.conf'
confclass = classes.sneakyTarget
pfile = './passwords.conf'

# Parse the things!
config, comm = confparsers.parseConfig(cfile, confclass,
                                       passfile=pfile,
                                       searchCommon=True,
                                       enableCheck=True,
                                       debug=True)

# Check to see if there are any connections/objects to establish
amqlistener = amq.silentSubscriber()
amqbrokers = {}
influxdatabases = {}

# NOTE: The idea is that basically ALL of what follows will become completely
#   generic boilerplate, to be shuffled away behind the scenes somewhere
#   for much easier access.  The only thing that might poke out is the stuff
#   above, but even that can be hidden away if we really need/want to do that.

# Since we can have multiple connections to a single broker or database or
#   whatever, we need to search through all of our defined sections to
#   pull out some of the specifics into one place; that makes our
#   connection/reconnection/subscription logic way easier
brokertopics = {}
for sect in config:
    csObj = config[sect]
    try:
        brokerTag = csObj.broker
        brokertype = comm[brokerTag].type
    except KeyError:
        # If we end up in here, we're completely hoopajooped so just give up
        break

    if brokertype.lower() == 'activemq':
        # Gather up broker stuff
        try:
            # First see if we have anything previously gathered, to make sure
            #   we don't accidentally clobber anything
            alltopics = brokertopics[brokerTag]
        except KeyError:
            alltopics = []

        # Get the topics; it's guaranteed to be a list so we can just add it
        thesetopics = amq.gatherAMQTopics(csObj)
        alltopics += thesetopics

        # list(set()) to quickly take care of any dupes
        brokertopics.update({brokerTag: list(set(alltopics))})

# Set up the actual connections, which we'll then give back to the actual
#   objects for them to do stuff with afterwards
for commsection in comm:
    # Rename for easier access/passing
    cobj = comm[commsection]

    # Now check the properties of this object to see if it's something we can
    #   actually regconize and then connect to
    if cobj.type.lower() == 'activemq':
        # We get brokerlistener back as a return just in case it was
        #   None initially, in which case amq.setupBroker would give one
        conn, amqlistener = amq.setupAMQBroker(cobj,
                                            brokertopics[commsection],
                                            listener=amqlistener)

        # Store this so we can check/use it later
        brokerbits = [conn, brokertopics[commsection], amqlistener]
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
        databases.update({commsection: idb})
    else:
        # No other types are defined yet
        pass

# This is intended to be inside of some loop structure from here on out,
#   but we're doing it in-line so we can just test the connection/subscription
#   and subsequent disconnection logic a little easier

if conn.conn is None:
    print("No connection at all! Retrying...")
        conn.connect(listener=crackers)
    elif conn.conn.transport.connected is False:
        print("Connection died! Reestablishing...")
        conn.connect(listener=crackers)
    else:
        print("Connection still valid")