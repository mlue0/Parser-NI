import { StyleSheet } from 'react-native';

export const colors = {
  black: '#000000',
  cyan: '#00FFF0',
  orange: '#FF6A00',
  primary: '#E6E6E6',
  secondary: '#BFBFBF'
};

export const styles = StyleSheet.create({
  header: { color: colors.primary, fontSize:28, fontWeight:'700' },
  subheader: { color: colors.secondary, fontSize:14, marginBottom:8 },
  label: { color: colors.secondary, fontSize:12, marginBottom:6, textTransform:'uppercase', letterSpacing:1 },
  input: { backgroundColor:'rgba(255,255,255,0.025)', borderWidth:1, borderColor:'rgba(0,255,240,0.12)', color: colors.primary, paddingHorizontal:14, paddingVertical:12, borderRadius:10 },
  fab: { backgroundColor: colors.orange, width:84, height:48, borderRadius:28, alignItems:'center', justifyContent:'center', alignSelf:'flex-end', marginTop:22 },
  statCard: { backgroundColor:'rgba(255,255,255,0.02)', borderRadius:14, padding:12, alignItems:'flex-start', justifyContent:'center' },
  statLabel: { color: colors.secondary, fontSize:12 },
  statNumber: { fontSize:36, fontWeight:'800', fontFamily: 'System' }
});

export default styles;
