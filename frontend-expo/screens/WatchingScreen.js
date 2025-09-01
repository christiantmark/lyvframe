import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Image, ScrollView, TouchableOpacity, Linking } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { getPeekShot } from '../api/flaskAPI';


const getTeamLogo = (code) => {
  switch (code.toLowerCase()) {
    case 'atl': return require('../assets/images/teams/atl.png');
    case 'bos': return require('../assets/images/teams/bos.png');
    case 'bkn': return require('../assets/images/teams/bkn.png');
    case 'cha': return require('../assets/images/teams/cha.png');
    case 'chi': return require('../assets/images/teams/chi.png');
    case 'cle': return require('../assets/images/teams/cle.png');
    case 'dal': return require('../assets/images/teams/dal.png');
    case 'den': return require('../assets/images/teams/den.png');
    case 'det': return require('../assets/images/teams/det.png');
    case 'gsw': return require('../assets/images/teams/gsw.png');
    case 'hou': return require('../assets/images/teams/hou.png');
    case 'ind': return require('../assets/images/teams/ind.png');
    case 'lac': return require('../assets/images/teams/lac.png');
    case 'lal': return require('../assets/images/teams/lal.png');
    case 'mem': return require('../assets/images/teams/mem.png');
    case 'mia': return require('../assets/images/teams/mia.png');
    case 'mil': return require('../assets/images/teams/mil.png');
    case 'min': return require('../assets/images/teams/min.png');
    case 'nop': return require('../assets/images/teams/nop.png');
    case 'nyk': return require('../assets/images/teams/nyk.png');
    case 'okc': return require('../assets/images/teams/okc.png');
    case 'orl': return require('../assets/images/teams/orl.png');
    case 'phi': return require('../assets/images/teams/phi.png');
    case 'phx': return require('../assets/images/teams/phx.png');
    case 'por': return require('../assets/images/teams/por.png');
    case 'sac': return require('../assets/images/teams/sac.png');
    case 'sas': return require('../assets/images/teams/sas.png');
    case 'tor': return require('../assets/images/teams/tor.png');
    case 'uta': return require('../assets/images/teams/uta.png');
    case 'was': return require('../assets/images/teams/was.png');
    default: return null;
  }
};

const buildEventUrl = (shot, gameId) => {
  const SEASON = "2024-25";
  // hardcoded season for now

  // Use the shot's actionNumber or fallback to empty string
  const gameEventId = shot?.actionNumber ?? "";

  if (!gameEventId) {
    console.warn("⚠️ Missing actionNumber for shot:", shot);
  }

  // Use the shot description as the title for the NBA URL
  const title = encodeURIComponent(shot?.description || "Shot");

  return `https://www.nba.com/stats/events?CFID=&CFPARAMS=&GameEventID=${gameEventId}&GameID=${gameId}&Season=${SEASON}&flag=1&title=${title}`;
};


const WatchingScreen = ({ route }) => {
  const navigation = useNavigation();
  const { homeTeamCode, awayTeamCode, clientId, gameId } = route.params;


  const [homeScore, setHomeScore] = useState(0);
  const [awayScore, setAwayScore] = useState(0);
  const [logs, setLogs] = useState([]);
  const [onCourt, setOnCourt] = useState({ home: [], away: [] });


  const scrollViewRef = useRef(null);


  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const newShot = await getPeekShot(clientId);
        if (newShot) {
          if (newShot.description && newShot.period && newShot.clock) {
            const formattedLog = `[Q${newShot.period} ${newShot.clock}] ${newShot.description}`;
            setLogs((prevLogs) => {
              if (prevLogs.length > 0 && prevLogs[prevLogs.length - 1].text === formattedLog) return prevLogs;

              return [...prevLogs, { text: formattedLog, url: buildEventUrl(newShot, gameId) }];
            });
          }
          if (newShot.scoreHome !== undefined) setHomeScore(newShot.scoreHome);
          if (newShot.scoreAway !== undefined) setAwayScore(newShot.scoreAway);
          if (newShot.onCourt) setOnCourt(newShot.onCourt);
        }
      } catch (err) {
        console.error('Error fetching new shot log:', err);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [clientId, gameId]);


  useEffect(() => {
    if (scrollViewRef.current) {
      scrollViewRef.current.scrollToEnd({ animated: true });
    }
  }, [logs]);


  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image source={getTeamLogo(awayTeamCode)} style={styles.teamLogo} />
        <Text style={styles.score}>{awayScore} - {homeScore}</Text>
        <Image source={getTeamLogo(homeTeamCode)} style={styles.teamLogo} />
      </View>


      <View style={styles.startersContainer}>
        <Text style={styles.startersHeader}>On Court</Text>


        <View style={styles.startersRow}>
          <Text style={styles.startersColumnHeader}>{awayTeamCode.toUpperCase()}</Text>
          <Text style={styles.startersColumnHeader}>{homeTeamCode.toUpperCase()}</Text>
        </View>

        {[0, 1, 2, 3, 4].map((i) => (
          <View style={styles.startersRow} key={i}>
            <TouchableOpacity
              style={styles.playerCell}
              onPress={() => {
                const player = onCourt.away?.[i];
                if (player) {
                  const playerWithId = { ...player, personId: player.id };
                  console.log("AWAY player pressed:", playerWithId);
                  console.log("gameId:", gameId);
                  navigation.navigate('PlayerProfile', { player: playerWithId, gameId });
                }
              }}
            >
              <Text style={styles.startersPlayer}>
                {onCourt.away?.[i]?.name || '-'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.playerCell}
              onPress={() => {
                const player = onCourt.home?.[i];
                if (player) {
                  const playerWithId = { ...player, personId: player.id };
                  console.log("HOME player pressed:", playerWithId);
                  console.log("gameId:", gameId);
                  navigation.navigate('PlayerProfile', { player: playerWithId, gameId });
                }
              }}
            >
              <Text style={styles.startersPlayer}>
                {onCourt.home?.[i]?.name || '-'}
              </Text>
            </TouchableOpacity>
          </View>
        ))}




      </View>


      <ScrollView style={styles.logsContainer} ref={scrollViewRef}>
        {logs.map((log, index) => (
          <TouchableOpacity
            key={index}
            onPress={() => log.url && Linking.openURL(log.url)}
          >
            <Text style={[styles.logText, { color: '#4da6ff' }]}>
              {log.text}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

    </View>
  );
};


const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#0f0f0f',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  teamLogo: {
    width: 64,
    height: 64,
    resizeMode: 'contain',
  },
  score: {
    fontSize: 36,
    fontWeight: 'bold',
    color: 'white',
  },
  startersContainer: {
    marginTop: 20,
    backgroundColor: '#1e1e1e',
    padding: 12,
    borderRadius: 10,
  },
  startersHeader: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
    color: 'white',
    textAlign: 'center',
  },
  startersRow: {
    flexDirection: 'row',
    justifyContent: 'center', // tighter spacing
    alignItems: 'center',
    marginVertical: 2, // less vertical spacing
  },
  startersColumnHeader: {
    fontWeight: 'bold',
    fontSize: 14,
    color: '#ccc',
    width: '45%',
    textAlign: 'center',
  },
  startersPlayer: {
    fontSize: 12,
    color: 'white',
    textAlign: 'center',
    paddingVertical: 0,
  },
  logsContainer: {
    flex: 1,
    marginTop: 16,
    backgroundColor: '#1a1a1a',
    padding: 10,
    borderRadius: 8,
  },
  logText: {
    color: '#ccc',
    marginBottom: 6,
    fontSize: 14,
  },
  playerCell: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 4,
  }

});


export default WatchingScreen;



