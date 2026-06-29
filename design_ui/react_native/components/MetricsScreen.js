import React from 'react';
import { View, Text, ScrollView } from 'react-native';
import { styles, colors } from '../styles';

const defects = ['Cont','CC','AD','INL','DNL','FC','Burn','U0'];

export default function MetricsScreen(){
  return (
    <ScrollView style={{flex:1, backgroundColor: colors.black, padding:18}}>
      <Text style={styles.header}>Metrics</Text>

      <View style={{flexDirection:'row', justifyContent:'space-between', marginTop:18}}>
        <View style={[styles.statCard, {flex:1, marginRight:8}]}> 
          <Text style={styles.statLabel}>Good Crystals</Text>
          <Text style={[styles.statNumber, {color: '#39FF66'}]}>1,248</Text>
        </View>
        <View style={[styles.statCard, {flex:1, marginLeft:8, marginRight:8}]}> 
          <Text style={styles.statLabel}>Defective Crystals</Text>
          <Text style={[styles.statNumber, {color: '#FF3B3B'}]}>24</Text>
        </View>
        <View style={[styles.statCard, {flex:1, marginLeft:8}]}> 
          <Text style={styles.statLabel}>Total Crystals</Text>
          <Text style={[styles.statNumber, {color: colors.cyan}]}>1,272</Text>
        </View>
      </View>

      <View style={{marginTop:22}}>
        <Text style={styles.subheader}>Defect Breakdown</Text>
        {defects.map(d => (
          <View key={d} style={{flexDirection:'row', justifyContent:'space-between', alignItems:'center', paddingVertical:8, borderBottomWidth:1, borderBottomColor:'rgba(255,255,255,0.02)'}}>
            <View style={{flexDirection:'row', alignItems:'center'}}>
              <View style={{width:10, height:10, borderRadius:10, backgroundColor: colors.cyan, marginRight:12}} />
              <Text style={{color:colors.primary}}>{d}</Text>
            </View>
            <Text style={{color:colors.primary}}> {Math.floor(Math.random()*20)}</Text>
          </View>
        ))}
      </View>

    </ScrollView>
  );
}
