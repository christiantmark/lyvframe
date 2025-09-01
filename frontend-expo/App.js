import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import SetupScreen from './screens/SetupScreen';
import DeviceSetupScreen from './screens/DeviceSetupScreen';
import GameSelectScreen from './screens/GameSelectScreen';
import LiveGameScreen from './screens/LiveGameScreen';
import ControlPanelScreen from './screens/ControlPanelScreen';
import WatchingScreen from './screens/WatchingScreen';
import PlayerProfile from './screens/PlayerProfile';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Setup">
        <Stack.Screen name="Setup" component={SetupScreen} />
        <Stack.Screen name="DeviceSetup" component={DeviceSetupScreen} />
        <Stack.Screen name="GameSelect" component={GameSelectScreen} />
        <Stack.Screen name="LiveGame" component={LiveGameScreen} />
        <Stack.Screen name="ControlPanel" component={ControlPanelScreen} />
        <Stack.Screen name="Watching" component={WatchingScreen} />
        <Stack.Screen name="PlayerProfile" component={PlayerProfile} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
