// screens/DeviceSetupScreen.js
import React from 'react';
import { View, Text, StyleSheet, Button } from 'react-native';

export default function DeviceSetupScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>NBA Shot Lights WiFi Setup</Text>
      <Button
        title="Next"
        onPress={() => navigation.navigate('GameSelect')}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, marginBottom: 20 },
});
