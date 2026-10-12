import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  useColorScheme,
  View
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Location from "expo-location";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import { NavigationContainer, DarkTheme, DefaultTheme } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar } from "expo-status-bar";
import { getCandidates, getNearby, saveFieldNote } from "./src/api";
import { Candidate } from "./src/types";

const Tabs = createBottomTabNavigator();

function Badge({ children, tone = "blue" }: { children: string; tone?: "blue" | "orange" | "green" }) {
  return <Text style={[styles.badge, styles[`badge${tone}`]]}>{children}</Text>;
}

function CandidateCard({
  item,
  onPress,
  dark
}: {
  item: Candidate;
  onPress: () => void;
  dark: boolean;
}) {
  return (
    <Pressable style={[styles.card, dark && styles.cardDark]} onPress={onPress}>
      <View style={styles.rowBetween}>
        <Text style={[styles.cardTitle, dark && styles.textLight]}>{item.district}</Text>
        <Badge tone={item.priority_band === "High" ? "orange" : "blue"}>{item.priority_band}</Badge>
      </View>
      <Text style={[styles.muted, dark && styles.textMuted]}>
        {item.class} · {(item.confidence * 100).toFixed(0)}% confidence
      </Text>
      <Text style={[styles.signal, dark && styles.textMuted]}>
        {item.candidate_rule_signals.join(" · ") || "No signals"}
      </Text>
    </Pressable>
  );
}

function HomeScreen({ navigation }: { navigation: any }) {
  const dark = useColorScheme() === "dark";
  const [items, setItems] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [district, setDistrict] = useState("");

  useEffect(() => {
    getCandidates()
      .then((result) => setItems(result.items))
      .catch(() => setError("Could not load candidates"))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(
    () => items.filter((item) => !district || item.district.toLowerCase().includes(district.toLowerCase())),
    [district, items]
  );

  return (
    <SafeAreaView style={[styles.screen, dark && styles.screenDark]}>
      <Text style={[styles.kicker, dark && styles.textMuted]}>KILNWATCH BD</Text>
      <Text style={[styles.title, dark && styles.textLight]}>Nearby candidates</Text>
      <Text style={[styles.advisory, dark && styles.advisoryDark]}>
        Advisory only: unverified screening candidates
      </Text>
      <TextInput
        value={district}
        onChangeText={setDistrict}
        placeholder="Filter district"
        placeholderTextColor={dark ? "#9aa4b2" : "#6b7280"}
        style={[styles.input, dark && styles.inputDark]}
      />
      {loading ? <ActivityIndicator color="#2563eb" style={styles.center} /> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {!loading && visible.length === 0 ? <Text style={[styles.empty, dark && styles.textMuted]}>No candidates</Text> : null}
      <FlatList
        data={visible}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <CandidateCard
            item={item}
            dark={dark}
            onPress={() => navigation.navigate("Map", { candidate: item })}
          />
        )}
      />
    </SafeAreaView>
  );
}

function MapScreen({ route, navigation }: { route: any; navigation: any }) {
  const dark = useColorScheme() === "dark";
  const selected = route.params?.candidate as Candidate | undefined;
  const [items, setItems] = useState<Candidate[]>(selected ? [selected] : []);
  const [region, setRegion] = useState({
    latitude: selected?.latitude ?? 23.7692,
    longitude: selected?.longitude ?? 90.4116,
    latitudeDelta: 0.4,
    longitudeDelta: 0.4
  });

  async function locate() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      Alert.alert("Location needed", "Allow location to find nearby candidates.");
      return;
    }
    const position = await Location.getCurrentPositionAsync({});
    const { latitude, longitude } = position.coords;
    setRegion({ latitude, longitude, latitudeDelta: 0.3, longitudeDelta: 0.3 });
    setItems(await getNearby(latitude, longitude));
  }

  return (
    <SafeAreaView style={[styles.screen, dark && styles.screenDark]}>
      <View style={styles.rowBetween}>
        <View>
          <Text style={[styles.kicker, dark && styles.textMuted]}>FIELD MAP</Text>
          <Text style={[styles.titleSmall, dark && styles.textLight]}>Candidate map</Text>
        </View>
        <Pressable style={styles.primaryButton} onPress={locate}>
          <Text style={styles.buttonText}>Find near me</Text>
        </Pressable>
      </View>
      <MapView provider={PROVIDER_GOOGLE} style={styles.map} region={region} showsUserLocation>
        {items.map((item) => (
          <Marker
            key={item.id}
            coordinate={{ latitude: item.latitude, longitude: item.longitude }}
            title={`Kiln candidate · ${item.district}`}
            description={`${item.priority_band} priority · ${(item.confidence * 100).toFixed(0)}% confidence`}
            onCalloutPress={() => navigation.navigate("Capture", { candidate: item })}
          />
        ))}
      </MapView>
      <Text style={[styles.advisory, dark && styles.advisoryDark]}>
        Tap a marker for field capture.
      </Text>
    </SafeAreaView>
  );
}

function CaptureScreen({ route }: { route: any }) {
  const dark = useColorScheme() === "dark";
  const candidate = route.params?.candidate as Candidate | undefined;
  const [note, setNote] = useState("");
  const [photoUri, setPhotoUri] = useState<string>();
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const [saving, setSaving] = useState(false);

  async function openCamera() {
    if (!cameraPermission?.granted) {
      const result = await requestCameraPermission();
      if (!result.granted) return;
    }
    setCameraOpen(true);
  }

  async function save() {
    if (!candidate) return;
    setSaving(true);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      const position = permission.status === "granted"
        ? await Location.getCurrentPositionAsync({})
        : undefined;
      await saveFieldNote(
        candidate.id,
        note,
        photoUri,
        position?.coords.latitude,
        position?.coords.longitude
      );
      Alert.alert("Saved", "Field note saved.");
      setNote("");
      setPhotoUri(undefined);
    } catch {
      Alert.alert("Demo saved", "Backend is offline. Keep this note for the demo.");
    } finally {
      setSaving(false);
    }
  }

  async function takePhoto() {
    const photo = await cameraRef.current?.takePictureAsync();
    if (photo?.uri) {
      setPhotoUri(photo.uri);
      setCameraOpen(false);
    }
  }

  if (cameraOpen) {
    return (
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        facing="back"
        onCameraReady={() => undefined}
      >
        <View style={styles.cameraControls}>
          <Pressable style={styles.cameraButton} onPress={takePhoto}>
            <Text style={styles.buttonText}>Take photo</Text>
          </Pressable>
          <Pressable style={styles.cameraButton} onPress={() => setCameraOpen(false)}>
            <Text style={styles.buttonText}>Close camera</Text>
          </Pressable>
        </View>
      </CameraView>
    );
  }

  return (
    <SafeAreaView style={[styles.screen, dark && styles.screenDark]}>
      <Text style={[styles.kicker, dark && styles.textMuted]}>FIELD CAPTURE</Text>
      <Text style={[styles.titleSmall, dark && styles.textLight]}>
        {candidate?.district ?? "Choose a candidate"}
      </Text>
      <Text style={[styles.muted, dark && styles.textMuted]}>
        {candidate ? `${candidate.class} · ${candidate.priority_band} priority` : "Open a marker first"}
      </Text>
      <TextInput
        value={note}
        onChangeText={setNote}
        placeholder="Add a note"
        placeholderTextColor={dark ? "#9aa4b2" : "#6b7280"}
        multiline
        style={[styles.note, dark && styles.inputDark]}
      />
      <View style={styles.row}>
        <Pressable style={styles.secondaryButton} onPress={openCamera}>
          <Text style={styles.secondaryText}>Take photo</Text>
        </Pressable>
        <Pressable style={styles.primaryButton} onPress={save} disabled={saving || !candidate}>
          <Text style={styles.buttonText}>{saving ? "Saving" : "Save note"}</Text>
        </Pressable>
      </View>
      {photoUri ? <Text style={styles.muted}>Photo ready</Text> : null}
      <Text style={[styles.advisory, dark && styles.advisoryDark]}>
        Screening note only.
      </Text>
    </SafeAreaView>
  );
}

export default function App() {
  const dark = useColorScheme() === "dark";
  return (
    <NavigationContainer theme={dark ? DarkTheme : DefaultTheme}>
      <StatusBar style={dark ? "light" : "dark"} />
      <Tabs.Navigator screenOptions={{ headerShown: false, tabBarActiveTintColor: "#2563eb" }}>
        <Tabs.Screen name="Home" component={HomeScreen} />
        <Tabs.Screen name="Map" component={MapScreen} />
        <Tabs.Screen name="Capture" component={CaptureScreen} />
      </Tabs.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, padding: 20, backgroundColor: "#f8fafc" },
  screenDark: { backgroundColor: "#111827" },
  kicker: { color: "#64748b", fontSize: 12, fontWeight: "800", letterSpacing: 1.4 },
  title: { color: "#0f172a", fontSize: 32, fontWeight: "800", marginTop: 8, marginBottom: 12 },
  titleSmall: { color: "#0f172a", fontSize: 24, fontWeight: "800", marginTop: 4 },
  textLight: { color: "#f8fafc" },
  textMuted: { color: "#9aa4b2" },
  advisory: { color: "#92400e", backgroundColor: "#fef3c7", borderRadius: 10, padding: 12, marginBottom: 14 },
  advisoryDark: { color: "#fde68a", backgroundColor: "#422006" },
  input: { backgroundColor: "#fff", borderColor: "#e2e8f0", borderRadius: 12, borderWidth: 1, padding: 14, marginBottom: 14 },
  inputDark: { backgroundColor: "#1f2937", borderColor: "#374151", color: "#f8fafc" },
  note: { minHeight: 140, textAlignVertical: "top", backgroundColor: "#fff", borderColor: "#e2e8f0", borderRadius: 12, borderWidth: 1, padding: 14, marginVertical: 20 },
  card: { backgroundColor: "#fff", borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: "#e2e8f0" },
  cardDark: { backgroundColor: "#1f2937", borderColor: "#374151" },
  cardTitle: { color: "#0f172a", fontSize: 17, fontWeight: "700" },
  muted: { color: "#64748b", marginTop: 5 },
  signal: { color: "#475569", marginTop: 10, fontSize: 12 },
  badge: { borderRadius: 99, paddingHorizontal: 10, paddingVertical: 5, overflow: "hidden", color: "#fff", fontSize: 12, fontWeight: "700" },
  badgeblue: { backgroundColor: "#2563eb" },
  badgeorange: { backgroundColor: "#d97706" },
  badgegreen: { backgroundColor: "#059669" },
  row: { flexDirection: "row", gap: 10, alignItems: "center" },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  primaryButton: { backgroundColor: "#2563eb", paddingHorizontal: 14, paddingVertical: 12, borderRadius: 10 },
  secondaryButton: { backgroundColor: "#dbeafe", paddingHorizontal: 14, paddingVertical: 12, borderRadius: 10 },
  buttonText: { color: "#fff", fontWeight: "700" },
  secondaryText: { color: "#1d4ed8", fontWeight: "700" },
  map: { flex: 1, minHeight: 420, borderRadius: 16, marginVertical: 14 },
  cameraButton: { alignSelf: "center", marginTop: 60, backgroundColor: "#111827", padding: 14, borderRadius: 10 },
  cameraControls: { flexDirection: "row", justifyContent: "center", gap: 10, marginTop: 60 },
  center: { marginTop: 40 },
  empty: { color: "#64748b", textAlign: "center", marginTop: 40 },
  error: { color: "#b91c1c", marginBottom: 10 }
});
