import React, {useState} from 'react';
import { SafeAreaView, View } from 'react-native';
import ParametersScreen from './components/ParametersScreen';
import MetricsScreen from './components/MetricsScreen';
import StandardsScreen from './components/StandardsScreen';
import BottomNav from './components/BottomNav';
import { colors } from './styles';

export default function App() {
  const [tab, setTab] = useState('Parameters');

  const renderScreen = () => {
    switch (tab) {
      case 'Parameters':
        return <ParametersScreen />;
      case 'Metrics':
        return <MetricsScreen />;
      case 'Standards':
        return <StandardsScreen />;
      default:
        return <ParametersScreen />;
    }
  };

  return (
    <SafeAreaView style={{flex:1, backgroundColor: colors.black}}>
      <View style={{flex:1}}>{renderScreen()}</View>
      <BottomNav active={tab} onChange={setTab} />
    </SafeAreaView>
  );
}
