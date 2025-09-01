// screens/ControlPanelScreen.js
import React from 'react';
import { View, Button, StyleSheet, Text } from 'react-native';
import { sendCommand } from '../api/flaskAPI';

export default function ControlPanelScreen() {
  const handleSendShot = async () => {
    try {
      await sendCommand('trigger_shot');
    } catch (e) {
      console.error('Shot trigger failed', e);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>NBA Shot Controller</Text>
      <Button title="Trigger Shot" onPress={handleSendShot} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
  },
  title: {
    fontSize: 24, marginBottom: 20,
  },
});
