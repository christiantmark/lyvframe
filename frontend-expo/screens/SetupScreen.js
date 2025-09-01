import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function SetupScreen({ navigation }) {
  const [clientId, setClientId] = useState('');
  const [sport, setSport] = useState('NBA');

  const handleNext = async () => {
    if (!clientId.trim()) {
      Alert.alert('Error', 'Please enter your Device ID');
      return;
    }

    try {
      await AsyncStorage.setItem('client_id', clientId);
      await AsyncStorage.setItem('sport', sport);
      navigation.navigate('GameSelect');
    } catch (err) {
      console.error('Error saving setup data', err);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>NBA Shot Lights WiFi Setup</Text>

      <Text style={styles.label}>Enter Device ID</Text>
      <TextInput
        style={styles.input}
        placeholder="e.g. device123"
        value={clientId}
        onChangeText={setClientId}
      />

      <Text style={styles.label}>Select a sport</Text>
      <Text style={styles.sport}>{sport}</Text>

      <Button title="Next →" onPress={handleNext} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    backgroundColor: '#fff',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 40,
    textAlign: 'center',
  },
  label: {
    fontSize: 16,
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#aaa',
    borderRadius: 6,
    padding: 10,
    marginBottom: 20,
  },
  sport: {
    fontSize: 18,
    marginBottom: 30,
    fontWeight: '500',
  },
});
