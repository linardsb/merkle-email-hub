#!/usr/bin/env node
/**
 * Generate React icon components from SVG source files.
 * Processes SVGs: removes hardcoded colors, uses currentColor, outputs TSX.
 *
 * Emits one file per icon under `src/components/icons/generated/` plus a
 * regenerated barrel at `src/components/icons/index.ts`.
 *
 * Usage:
 *   node scripts/generate-icons.mjs
 *   pnpm exec prettier --write src/components/icons   # always re-format after regenerating
 */
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ICONS_ROOT = resolve(__dirname, "../../../../email-templates/Icons");
const OUTPUT_DIR = resolve(__dirname, "../src/components/icons");

// ── Icon Mapping ─────────────────────────────────────────────────────
// key = React export name (matches lucide-react naming)
// value = { source: 'brand'|'small'|'stroke', path: relative to ICONS_ROOT }
const ICON_MAP = {
  // ══════════════════════════════════════════════════════════════════════
  // BRAND ICONS (32×32, Merkle Brand library)
  // ══════════════════════════════════════════════════════════════════════

  // ── AI ─────────────────────────────────────────────────────────────
  Brain: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-brain-black.svg" },
  Bot: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-person-black.svg" },
  Sparkles: {
    source: "brand",
    path: "Merkle Brand/Artificial Intelligence/32x32-AI-idea-black.svg",
  },
  Code: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-chip-black.svg" },
  Code2: { source: "brand", path: "Merkle Brand/Artificial Intelligence/32x32-AI-chip-black.svg" },
  Lightbulb: {
    source: "brand",
    path: "Merkle Brand/Artificial Intelligence/32x32-AI-idea-black.svg",
  },

  // ── Digital Marketing ──────────────────────────────────────────────
  Mail: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Email-black.svg",
  },
  MailOpen: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-email-2-black.svg",
  },
  Search: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-search-black.svg",
  },
  SearchLaptop: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-search-laptop-black.svg",
  },
  MessageSquare: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Online-Chat-black.svg",
  },
  Cloud: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Cloud-black.svg",
  },
  CloudUpload: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Cloud-black.svg",
  },
  Package: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Package-black.svg",
  },
  Palette: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  Paintbrush: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  Wand2: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  PenTool: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Creative-black.svg",
  },
  Activity: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Metrics-black.svg",
  },
  Calendar: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Alarm-black.svg",
  },
  Puzzle: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Problem-Solving-black.svg",
  },
  Play: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Submit-Click-black.svg",
  },
  ClipboardCheck: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-checklist-black.svg",
  },
  ClipboardList: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-checklist-black.svg",
  },
  ListChecks: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-checklist-black.svg",
  },
  Network: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Networking-black.svg",
  },
  Workflow: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Settings-black.svg",
  },
  Cog: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Settings-black.svg",
  },
  Send: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Launch-black.svg",
  },
  Users: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Large-Team-black.svg",
  },
  User: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Individual-Avatar-black.svg",
  },
  UserCheck: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Checkmark-black.svg",
  },
  BookOpen: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Knowledge-black.svg",
  },
  LayoutDashboard: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Pie-Chart-black.svg",
  },
  BarChart3: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Data-Report-black.svg",
  },
  // New brand DM icons
  Achievement: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Achievement-black.svg",
  },
  Megaphone: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Announcements-black.svg",
  },
  AppWindow: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Browser-black.svg",
  },
  BrowserSettings: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Browser-Settings-black.svg",
  },
  ShoppingCart: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Cart-black.svg",
  },
  PhoneCall: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Communication-black.svg",
  },
  MessagesSquare: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Communication-Discussion-black.svg",
  },
  HeadphonesSupport: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Customer-Service-black.svg",
  },
  DataScientist: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Data-Scientist-black.svg",
  },
  DigitalAnalysis: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Digital-Analysis-black.svg",
  },
  Idea: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-idea-black.svg",
  },
  UsersFemale: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Female-black.svg",
  },
  UsersMale: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Male-black.svg",
  },
  UserProfessionalM: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-male-professional-black.svg",
  },
  UserProfessionalF: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-female-professional-black.svg",
  },
  GraduationCap: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Graduate-black.svg",
  },
  UsersGroup: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Group-Discussion-black.svg",
  },
  ThumbsUp: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-like-black.svg",
  },
  Audience: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Audience-black.svg",
  },
  Handshake: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Collaboration-black.svg",
  },
  BadgeCheck: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Identity-black.svg",
  },
  BookMarked: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Learning-black.svg",
  },
  Partnership: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Partnership-black.svg",
  },
  PartnershipTwo: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Partnership-Two-black.svg",
  },
  Presentation: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Identifying-Presentation-black.svg",
  },
  PresentationAdvisor: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Presentation-Advisor-black.svg",
  },
  PersonTalking: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Person-Talking-black.svg",
  },
  TwoPeopleTalking: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Two-People-Talking-black.svg",
  },
  CirclePlus: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-plus-black.svg",
  },
  SquarePlus: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Plus-box-black.svg",
  },
  ThumbsDown: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Problem-like-black.svg",
  },
  ShoppingBag: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Shopping-Cart-black.svg",
  },
  Store: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-Storefront-black.svg",
  },
  CircleX: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-X-black.svg",
  },
  SquareX: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-X-box-black.svg",
  },
  Laptop: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Electronics-Laptop-black.svg",
  },
  Wifi: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Electronics-Device-Wifi-black.svg",
  },
  DesktopDM: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Electronics-desktop-black.svg",
  },
  Departures: {
    source: "brand",
    path: "Merkle Brand/Digital Marketing/32x32-Digital-Marketng-departures-black.svg",
  },

  // ── Electronics ────────────────────────────────────────────────────
  Camera: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-Camera-black.svg" },
  Mic: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-microphone-black.svg" },
  Monitor: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-desktop-black.svg",
  },
  MonitorSmartphone: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Mobile-Tablet-black.svg",
  },
  Tablet: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Mobile-Tablet-black.svg",
  },
  Smartphone: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-mobile-black.svg",
  },
  Key: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg" },
  KeyRound: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  Shield: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  ShieldAlert: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  ShieldCheck: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  ShieldX: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Security-black.svg",
  },
  Plug: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Enviroment-Electric-Plug-black.svg",
  },
  // New electronics
  Gamepad: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-Gaming-black.svg" },
  GamepadController: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Gaming-Controller-black.svg",
  },
  Headset: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Headset-black.svg",
  },
  Keyboard: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-keyboard-black.svg",
  },
  LaptopElec: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Laptop-black.svg",
  },
  Mouse: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-mouse-black.svg" },
  Router: { source: "brand", path: "Merkle Brand/Electronics/32x32-Electronics-Router-black.svg" },
  WifiElec: {
    source: "brand",
    path: "Merkle Brand/Electronics/32x32-Electronics-Device-Wifi-black.svg",
  },

  // ── Environment ────────────────────────────────────────────────────
  Globe: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Global-black.svg" },
  Sun: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Sun-black.svg" },
  Zap: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Electric-black.svg" },
  // New environment
  CleanEnergy: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Clean-Energy-black.svg",
  },
  Diamond: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Diamond-black.svg" },
  ShoppingBagEco: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Eco-Bag-black.svg",
  },
  Home: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Efficient-Home-black.svg",
  },
  CarElectric: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Electric-Cars-black.svg",
  },
  Fuel: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Electric-Oil-black.svg",
  },
  LeafHeart: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Environmentally-Friendly-black.svg",
  },
  Factory: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Factory-black.svg" },
  WindTurbine: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Green-Energy-black.svg",
  },
  HandHeart: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Green-Support-black.svg",
  },
  Sprout: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Growth-black.svg" },
  Leaf: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Leaf-black.svg" },
  Recycle: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Recycle-black.svg" },
  TreePine: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Trees-black.svg" },
  Trash: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Waste-black.svg" },
  Waves: { source: "brand", path: "Merkle Brand/Environment/32x32-Enviroment-Watter-black.svg" },
  Droplet: {
    source: "brand",
    path: "Merkle Brand/Environment/32x32-Enviroment-Watter-drop-black.svg",
  },

  // ── Finance ────────────────────────────────────────────────────────
  Target: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Target-black.svg" },
  FileText: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Document-black.svg" },
  Building2: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Bank-black.svg" },
  FolderOpen: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-briefcase-black.svg" },
  TrendingUp: {
    source: "brand",
    path: "Merkle Brand/Finance/32x32-Finance-Financial-Growth-black.svg",
  },
  Trophy: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Trophy-black.svg" },
  // New finance
  CreditCard: { source: "brand", path: "Merkle Brand/Finance/32x32--Finance-Card-black.svg" },
  Bitcoin: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-bit-coin-black.svg" },
  Calculator: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Calculator-black.svg" },
  Banknote: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Cash-black.svg" },
  CoinStack: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Coin-stack-black.svg" },
  CoinEuro: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Coin-euro-black.svg" },
  CoinPound: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Coin-pound-black.svg" },
  CoinYen: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Coin-yen-black.svg" },
  Wallet: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Crypto-Wallet-black.svg" },
  CurrencyExchange: {
    source: "brand",
    path: "Merkle Brand/Finance/32x32-Finance-Currency-Exchange-black.svg",
  },
  ScaleBalance: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Decisions-black.svg" },
  TrendingDown: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-decline-black.svg" },
  ChartDown: {
    source: "brand",
    path: "Merkle Brand/Finance/32x32-Finance-Financial-Decline-black.svg",
  },
  SearchDollar: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Find-Coin-black.svg" },
  ArrowUpRight: {
    source: "brand",
    path: "Merkle Brand/Finance/32x32-Finance-forward-momentum-black.svg",
  },
  ChartUp: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-growth-black.svg" },
  MailMoney: {
    source: "brand",
    path: "Merkle Brand/Finance/32x32-Finance-Mailing-Money-black.svg",
  },
  MoneyBag: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Money-bag-black.svg" },
  HandCoins: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Payment-black.svg" },
  ReceiptRefund: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Refiund-black.svg" },
  Strategy: { source: "brand", path: "Merkle Brand/Finance/32x32-Finance-Strategy-black.svg" },

  // ── Food ───────────────────────────────────────────────────────────
  Hamburger: { source: "brand", path: "Merkle Brand/Food/32x32-food-bev-hamburger-black.svg" },
  Pizza: { source: "brand", path: "Merkle Brand/Food/32x32-food-bev-pizza-black.svg" },
  UtensilsCrossed: { source: "brand", path: "Merkle Brand/Food/32x32-food-bev-plate-black.svg" },
  Restaurant: {
    source: "brand",
    path: "Merkle Brand/Food/32x32-food-bev-sit-down-restaurant-black.svg",
  },

  // ── Travel ─────────────────────────────────────────────────────────
  Compass: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Compass-black.svg" },
  Bike: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Bicycle-black.svg" },
  Ship: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Boat-black.svg" },
  Bus: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Bus-black.svg" },
  Car: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Car-black.svg" },
  CruiseShip: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-cruise-ship-black.svg" },
  Truck: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Delivery-black.svg" },
  MapSearch: {
    source: "brand",
    path: "Merkle Brand/Travel/32x32-Travel-Finding-Business-black.svg",
  },
  Flag: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Flag-black.svg" },
  PlaneTakeoff: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-flight-black.svg" },
  MapPin: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-GPS-black.svg" },
  Helicopter: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Hellcopter-black.svg" },
  Map: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Maps-black.svg" },
  Pin: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Pin-black.svg" },
  Plane: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Plane-black.svg" },
  Train: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Railway-black.svg" },
  Route: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Route-black.svg" },
  SemiTruck: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Semi-Truck-black.svg" },
  ShippingBoat: {
    source: "brand",
    path: "Merkle Brand/Travel/32x32-Travel-shipping-boat-black.svg",
  },
  Beads: { source: "brand", path: "Merkle Brand/Travel/32x32-Travel-Bead-black.svg" },

  // ══════════════════════════════════════════════════════════════════════
  // SMALL ICONS (256×256, fill style)
  // ══════════════════════════════════════════════════════════════════════

  // ── Previously mapped ──────────────────────────────────────────────
  Blocks: { source: "small", path: "Small Icons/Electronics and Devices/circuitry-fill.svg" },
  Inbox: { source: "small", path: "Small Icons/Travel/mailbox-fill.svg" },
  Server: { source: "small", path: "Small Icons/Data Analysis /hard-drives-fill.svg" },
  FileCode: { source: "small", path: "Small Icons/Electronics and Devices/code-block-fill.svg" },
  FileSpreadsheet: { source: "small", path: "Small Icons/Data Analysis /file-csv-fill.svg" },
  GitBranch: { source: "small", path: "Small Icons/Data Analysis /tree-structure-fill.svg" },
  UserRoundPen: { source: "small", path: "Small Icons/People/user-gear-fill.svg" },
  Layers: { source: "small", path: "Small Icons/Travel/books-fill.svg" },
  Database: { source: "small", path: "Small Icons/Electronics and Devices/database-fill.svg" },
  Download: { source: "small", path: "Small Icons/Travel/rocket-launch-fill.svg" },
  Upload: { source: "small", path: "Small Icons/Travel/rocket-fill.svg" },
  Eye: { source: "small", path: "Small Icons/Travel/compass-fill.svg" },
  Printer: { source: "small", path: "Small Icons/Data Analysis /presentation-chart-fill.svg" },
  History: { source: "small", path: "Small Icons/Travel/signpost-fill.svg" },
  Clock: { source: "small", path: "Small Icons/Travel/compass-fill.svg" },

  // ── Small: Data Analysis ───────────────────────────────────────────
  ChartBarSmall: { source: "small", path: "Small Icons/Data Analysis /chart-bar-fill.svg" },
  ChartBarH: { source: "small", path: "Small Icons/Data Analysis /chart-bar-horizontal-fill.svg" },
  ChartDonut: { source: "small", path: "Small Icons/Data Analysis /chart-donut-fill.svg" },
  ChartLine: { source: "small", path: "Small Icons/Data Analysis /chart-line-fill.svg" },
  ChartLineUp: { source: "small", path: "Small Icons/Data Analysis /chart-line-up-fill.svg" },
  ChartPie: { source: "small", path: "Small Icons/Data Analysis /chart-pie-fill.svg" },
  ChartPieSlice: { source: "small", path: "Small Icons/Data Analysis /chart-pie-slice-fill.svg" },
  ChartPolar: { source: "small", path: "Small Icons/Data Analysis /chart-polar-fill.svg" },
  ChartScatter: { source: "small", path: "Small Icons/Data Analysis /chart-scatter-fill.svg" },
  FileSql: { source: "small", path: "Small Icons/Data Analysis /file-sql-fill.svg" },
  HardDrive: { source: "small", path: "Small Icons/Data Analysis /hard-drive-fill.svg" },
  PresentationChart: {
    source: "small",
    path: "Small Icons/Data Analysis /presentation-chart-fill.svg",
  },
  PresentationSmall: { source: "small", path: "Small Icons/Data Analysis /presentation-fill.svg" },
  ProjectorScreen: {
    source: "small",
    path: "Small Icons/Data Analysis /projector-screen-fill.svg",
  },
  ProjectorChart: {
    source: "small",
    path: "Small Icons/Data Analysis /projector-screen-chart-fill.svg",
  },
  TreeStructure: { source: "small", path: "Small Icons/Data Analysis /tree-structure-fill.svg" },
  TrendDownSmall: { source: "small", path: "Small Icons/Data Analysis /trend-down-fill.svg" },
  TrendUpSmall: { source: "small", path: "Small Icons/Data Analysis /trend-up-fill.svg" },

  // ── Small: Electronics & Devices ───────────────────────────────────
  Atom: { source: "small", path: "Small Icons/Electronics and Devices/atom-fill.svg" },
  Cpu: { source: "small", path: "Small Icons/Electronics and Devices/cpu-fill.svg" },
  Circuitry: { source: "small", path: "Small Icons/Electronics and Devices/circuitry-fill.svg" },
  DesktopSmall: { source: "small", path: "Small Icons/Electronics and Devices/desktop-fill.svg" },
  DesktopTower: {
    source: "small",
    path: "Small Icons/Electronics and Devices/desktop-tower-fill.svg",
  },
  DeviceMobile: {
    source: "small",
    path: "Small Icons/Electronics and Devices/device-mobile-fill.svg",
  },
  DeviceTablet: {
    source: "small",
    path: "Small Icons/Electronics and Devices/device-tablet-fill.svg",
  },
  Devices: { source: "small", path: "Small Icons/Electronics and Devices/devices-fill.svg" },
  HeadCircuit: {
    source: "small",
    path: "Small Icons/Electronics and Devices/head-circuit-fill.svg",
  },
  Memory: { source: "small", path: "Small Icons/Electronics and Devices/memory-fill.svg" },

  // ── Small: Finance ─────────────────────────────────────────────────
  BankSmall: { source: "small", path: "Small Icons/Finance/bank-fill.svg" },
  CalculatorSmall: { source: "small", path: "Small Icons/Finance/calculator-fill.svg" },
  CardHolder: { source: "small", path: "Small Icons/Finance/cardholder-fill.svg" },
  Coin: { source: "small", path: "Small Icons/Finance/coin-fill.svg" },
  CoinVertical: { source: "small", path: "Small Icons/Finance/coin-vertical-fill.svg" },
  Coins: { source: "small", path: "Small Icons/Finance/coins-fill.svg" },
  CreditCardSmall: { source: "small", path: "Small Icons/Finance/credit-card-fill.svg" },
  CurrencyDollar: { source: "small", path: "Small Icons/Finance/currency-dollar-fill.svg" },
  CurrencyEur: { source: "small", path: "Small Icons/Finance/currency-eur-fill.svg" },
  CurrencyBtc: { source: "small", path: "Small Icons/Finance/currency-btc-fill.svg" },
  Invoice: { source: "small", path: "Small Icons/Finance/invoice-fill.svg" },
  MoneySmall: { source: "small", path: "Small Icons/Finance/money-fill.svg" },
  PiggyBank: { source: "small", path: "Small Icons/Finance/piggy-bank-fill.svg" },
  Receipt: { source: "small", path: "Small Icons/Finance/receipt-fill.svg" },
  StrategySmall: { source: "small", path: "Small Icons/Finance/strategy-fill.svg" },
  TipJar: { source: "small", path: "Small Icons/Finance/tip-jar-fill.svg" },
  WalletSmall: { source: "small", path: "Small Icons/Finance/wallet-fill.svg" },

  // ── Small: People ──────────────────────────────────────────────────
  Baby: { source: "small", path: "Small Icons/People/baby-fill.svg" },
  BabyCarriage: { source: "small", path: "Small Icons/People/baby-carriage-fill.svg" },
  Detective: { source: "small", path: "Small Icons/People/detective-fill.svg" },
  HandshakeSmall: { source: "small", path: "Small Icons/People/handshake-fill.svg" },
  HandWaving: { source: "small", path: "Small Icons/People/hand-waving-fill.svg" },
  HandFist: { source: "small", path: "Small Icons/People/hand-fist-fill.svg" },
  HandPeace: { source: "small", path: "Small Icons/People/hand-peace-fill.svg" },
  HandCoinsSmall: { source: "small", path: "Small Icons/People/hand-coins-fill.svg" },
  IdBadge: { source: "small", path: "Small Icons/People/identification-badge-fill.svg" },
  IdCard: { source: "small", path: "Small Icons/People/identification-card-fill.svg" },
  Person: { source: "small", path: "Small Icons/People/person-fill.svg" },
  PersonArmsSpread: { source: "small", path: "Small Icons/People/person-arms-spread-fill.svg" },
  PersonRun: { source: "small", path: "Small Icons/People/person-simple-run-fill.svg" },
  PersonWalk: { source: "small", path: "Small Icons/People/person-simple-walk-fill.svg" },
  PersonBike: { source: "small", path: "Small Icons/People/person-simple-bike-fill.svg" },
  PersonSwim: { source: "small", path: "Small Icons/People/person-simple-swim-fill.svg" },
  PersonHike: { source: "small", path: "Small Icons/People/person-simple-hike-fill.svg" },
  Student: { source: "small", path: "Small Icons/People/student-fill.svg" },
  SmileyHappy: { source: "small", path: "Small Icons/People/smiley-fill.svg" },
  SmileyWink: { source: "small", path: "Small Icons/People/smiley-wink-fill.svg" },
  LegoSmiley: { source: "small", path: "Small Icons/People/lego-smiley-fill.svg" },
  ThumbsUpSmall: { source: "small", path: "Small Icons/People/thumbs-up-fill.svg" },
  ThumbsDownSmall: { source: "small", path: "Small Icons/People/thumbs-down-fill.svg" },
  UserCircle: { source: "small", path: "Small Icons/People/user-circle-fill.svg" },
  UserFocus: { source: "small", path: "Small Icons/People/user-focus-fill.svg" },
  UserList: { source: "small", path: "Small Icons/People/user-list-fill.svg" },
  UserPlus: { source: "small", path: "Small Icons/People/user-plus-fill.svg" },
  UsersMini: { source: "small", path: "Small Icons/People/users-fill.svg" },
  UsersThree: { source: "small", path: "Small Icons/People/users-three-fill.svg" },
  UsersFour: { source: "small", path: "Small Icons/People/users-four-fill.svg" },

  // ── Small: Environment ─────────────────────────────────────────────
  FlowerLotus: { source: "small", path: "Small Icons/Environment/flower-lotus-fill.svg" },
  FlowerTulip: { source: "small", path: "Small Icons/Environment/flower-tulip-fill.svg" },
  Flower: { source: "small", path: "Small Icons/Environment/flower-fill.svg" },
  LeafSmall: { source: "small", path: "Small Icons/Environment/leaf-fill.svg" },
  RecycleSmall: { source: "small", path: "Small Icons/Environment/recycle-fill.svg" },
  TreeSmall: { source: "small", path: "Small Icons/Environment/tree-fill.svg" },
  TreeEvergreen: { source: "small", path: "Small Icons/Environment/tree-evergreen-fill.svg" },
  TreePalm: { source: "small", path: "Small Icons/Environment/tree-palm-fill.svg" },

  // ── Small: Travel ──────────────────────────────────────────────────
  AirplaneSmall: { source: "small", path: "Small Icons/Travel/airplane-fill.svg" },
  AirplaneTakeoff: { source: "small", path: "Small Icons/Travel/airplane-takeoff-fill.svg" },
  AirplaneLanding: { source: "small", path: "Small Icons/Travel/airplane-landing-fill.svg" },
  Ambulance: { source: "small", path: "Small Icons/Travel/ambulance-fill.svg" },
  Anchor: { source: "small", path: "Small Icons/Travel/anchor-fill.svg" },
  Binoculars: { source: "small", path: "Small Icons/Travel/binoculars-fill.svg" },
  Boat: { source: "small", path: "Small Icons/Travel/boat-fill.svg" },
  BridgeSmall: { source: "small", path: "Small Icons/Travel/bridge-fill.svg" },
  BuildingSmall: { source: "small", path: "Small Icons/Travel/building-fill.svg" },
  BuildingApart: { source: "small", path: "Small Icons/Travel/building-apartment-fill.svg" },
  BuildingOffice: { source: "small", path: "Small Icons/Travel/building-office-fill.svg" },
  Buildings: { source: "small", path: "Small Icons/Travel/buildings-fill.svg" },
  BusSmall: { source: "small", path: "Small Icons/Travel/bus-fill.svg" },
  CarSmall: { source: "small", path: "Small Icons/Travel/car-fill.svg" },
  Church: { source: "small", path: "Small Icons/Travel/church-fill.svg" },
  City: { source: "small", path: "Small Icons/Travel/city-fill.svg" },
  CompassSmall: { source: "small", path: "Small Icons/Travel/compass-fill.svg" },
  CompassRose: { source: "small", path: "Small Icons/Travel/compass-rose-fill.svg" },
  FlagSmall: { source: "small", path: "Small Icons/Travel/flag-fill.svg" },
  FlagBanner: { source: "small", path: "Small Icons/Travel/flag-banner-fill.svg" },
  FlagCheckered: { source: "small", path: "Small Icons/Travel/flag-checkered-fill.svg" },
  Footprints: { source: "small", path: "Small Icons/Travel/footprints-fill.svg" },
  GpsSmall: { source: "small", path: "Small Icons/Travel/gps-fill.svg" },
  GpsFix: { source: "small", path: "Small Icons/Travel/gps-fix-fill.svg" },
  HouseSmall: { source: "small", path: "Small Icons/Travel/house-fill.svg" },
  Island: { source: "small", path: "Small Icons/Travel/island-fill.svg" },
  Lighthouse: { source: "small", path: "Small Icons/Travel/lighthouse-fill.svg" },
  MapPinSmall: { source: "small", path: "Small Icons/Travel/map-pin-fill.svg" },
  MapTrifold: { source: "small", path: "Small Icons/Travel/map-trifold-fill.svg" },
  Motorcycle: { source: "small", path: "Small Icons/Travel/motorcycle-fill.svg" },
  PaperPlane: { source: "small", path: "Small Icons/Travel/paper-plane-fill.svg" },
  PaperPlaneTilt: { source: "small", path: "Small Icons/Travel/paper-plane-tilt-fill.svg" },
  Park: { source: "small", path: "Small Icons/Travel/park-fill.svg" },
  Path: { source: "small", path: "Small Icons/Travel/path-fill.svg" },
  PoliceCar: { source: "small", path: "Small Icons/Travel/police-car-fill.svg" },
  PushPin: { source: "small", path: "Small Icons/Travel/push-pin-fill.svg" },
  RoadHorizon: { source: "small", path: "Small Icons/Travel/road-horizon-fill.svg" },
  Rocket: { source: "small", path: "Small Icons/Travel/rocket-fill.svg" },
  RocketLaunch: { source: "small", path: "Small Icons/Travel/rocket-launch-fill.svg" },
  Sailboat: { source: "small", path: "Small Icons/Travel/sailboat-fill.svg" },
  ShippingContainer: { source: "small", path: "Small Icons/Travel/shipping-container-fill.svg" },
  Signpost: { source: "small", path: "Small Icons/Travel/signpost-fill.svg" },
  Suitcase: { source: "small", path: "Small Icons/Travel/suitcase-rolling-fill.svg" },
  Taxi: { source: "small", path: "Small Icons/Travel/taxi-fill.svg" },
  Tent: { source: "small", path: "Small Icons/Travel/tent-fill.svg" },
  TrainSmall: { source: "small", path: "Small Icons/Travel/train-fill.svg" },
  TrainRegional: { source: "small", path: "Small Icons/Travel/train-regional-fill.svg" },
  TruckSmall: { source: "small", path: "Small Icons/Travel/truck-fill.svg" },
  Van: { source: "small", path: "Small Icons/Travel/van-fill.svg" },
  Warehouse: { source: "small", path: "Small Icons/Travel/warehouse-fill.svg" },

  // ══════════════════════════════════════════════════════════════════════
  // EDITABLE-STROKE (dotted/business/travel outlines)
  // ══════════════════════════════════════════════════════════════════════
  FlaskConical: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_beaker-science_06.svg",
  },
  BrainDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_brain-smart_07.svg",
  },
  ChartBarDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_chart-bar-data_04.svg",
  },
  ChessDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_chess-strategy_18.svg",
  },
  CompassDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_compass-strategy_15.svg",
  },
  CursorClick: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_cursor-click_01.svg",
  },
  Fingerprint: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_finger-print-identity_08.svg",
  },
  GearDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_gear-settings_17.svg",
  },
  Gem: { source: "stroke", path: "editable-stroke/dotted-icons/Icon_dotted_gem-diamond_12.svg" },
  Heart: { source: "stroke", path: "editable-stroke/dotted-icons/Icon_dotted_heart-like_13.svg" },
  LetterSend: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_letter-send-email_19.svg",
  },
  LightbulbDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_light-bulb-idea_03.svg",
  },
  MagnifierDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_magnifier-search_05.svg",
  },
  PinDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_pin-location-marker_14.svg",
  },
  MonitorDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_screen-monitor_11.svg",
  },
  BasketDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_shopping-basket-commerce_10.svg",
  },
  CartDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_shopping-cart-commerce_02.svg",
  },
  ThunderDotted: {
    source: "stroke",
    path: "editable-stroke/dotted-icons/Icon_dotted_thunder-bolt-lightning_09.svg",
  },
};

// ── SVG Processing ───────────────────────────────────────────────────

function processBrandSvg(content) {
  // Remove XML declaration
  content = content.replace(/<\?xml[^?]*\?>\s*/g, "");

  // Extract style classes → fill values
  const styleMap = {};
  const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/);
  if (styleMatch) {
    for (const rule of styleMatch[1].matchAll(/\.([\w-]+)\s*\{([^}]*)\}/g)) {
      const className = rule[1];
      const fillMatch = rule[2].match(/fill:\s*([^;]+)/);
      if (fillMatch) {
        styleMap[className] = fillMatch[1].trim();
      }
    }
  }

  // Remove <defs>...</defs> and <style>...</style> (may appear outside defs).
  // Loop until stable: nested/overlapping tags can survive a single pass.
  let prevContent;
  do {
    prevContent = content;
    content = content.replace(/<defs>[\s\S]*?<\/defs>\s*/g, "");
    content = content.replace(/<style[^>]*>[\s\S]*?<\/style>\s*/g, "");
  } while (content !== prevContent);

  // Replace class references
  content = content.replace(/\s*class="([\w-]+)"/g, (_match, className) => {
    const fill = styleMap[className];
    if (fill === "none") return ' fill="none"';
    return ""; // will inherit currentColor
  });

  // Extract viewBox
  const viewBoxMatch = content.match(/viewBox="([^"]+)"/);
  const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 32 32";

  // Extract inner content
  const innerMatch = content.match(/<svg[^>]*>([\s\S]*)<\/svg>/);
  let inner = innerMatch ? innerMatch[1].trim() : "";

  // Clean attributes
  inner = inner
    .replace(/\s*id="[^"]*"/g, "")
    .replace(/\s*data-name="[^"]*"/g, "")
    .replace(/\s*xmlns:xlink="[^"]*"/g, "");

  // Remove empty groups (repeat to handle nesting)
  for (let i = 0; i < 3; i++) {
    inner = inner.replace(/<g\s*>([\s\S]*?)<\/g>/g, "$1");
  }

  return { viewBox, inner };
}

function processSmallSvg(content) {
  // These are simple: single fill color on <svg>, paths inside
  const viewBoxMatch = content.match(/viewBox="([^"]+)"/);
  const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 256 256";

  const innerMatch = content.match(/<svg[^>]*>([\s\S]*)<\/svg>/);
  let inner = innerMatch ? innerMatch[1].trim() : "";

  // Remove <defs>...</defs> and <style>...</style> blocks.
  // Loop until stable: nested/overlapping tags can survive a single pass.
  let prevInner;
  do {
    prevInner = inner;
    inner = inner.replace(/<defs>[\s\S]*?<\/defs>\s*/g, "");
    inner = inner.replace(/<style[^>]*>[\s\S]*?<\/style>\s*/g, "");
  } while (inner !== prevInner);

  // Remove class attributes (styles already removed)
  inner = inner.replace(/\s*class="[^"]*"/g, "");

  // Remove any fill attributes from inner paths (they'll inherit currentColor)
  inner = inner.replace(/\s*fill="[^"]*"/g, "");

  return { viewBox, inner };
}

function processStrokeSvg(content) {
  const viewBoxMatch = content.match(/viewBox="([^"]+)"/);
  const viewBox = viewBoxMatch ? viewBoxMatch[1] : "0 0 72 65";

  const innerMatch = content.match(/<svg[^>]*>([\s\S]*)<\/svg>/);
  let inner = innerMatch ? innerMatch[1].trim() : "";

  // Replace hardcoded stroke color with currentColor
  inner = inner.replace(/stroke="#[0-9a-fA-F]+"/g, 'stroke="currentColor"');

  // Replace hardcoded fill colors with currentColor (but not fill="none")
  inner = inner.replace(/fill="#[0-9a-fA-F]+"/g, 'fill="currentColor"');

  // Clean IDs and data attributes
  inner = inner.replace(/\s*id="[^"]*"/g, "").replace(/\s*data-name="[^"]*"/g, "");

  // Remove ALL <g> tags (opening with any attrs, and closing) — flatten structure
  inner = inner.replace(/<g[^>]*>/g, "").replace(/<\/g>/g, "");

  return { viewBox, inner, isStroke: true };
}

// ── JSX conversion ───────────────────────────────────────────────────

function svgInnerToJsx(inner) {
  // Remove HTML/XML comments (invalid in JSX).
  // Loop until stable: nested/overlapping comment markers can survive a single pass.
  let prevInner;
  do {
    prevInner = inner;
    inner = inner.replace(/<!--[\s\S]*?-->/g, "");
  } while (inner !== prevInner);

  // Convert SVG attributes to JSX camelCase
  return (
    inner
      .replace(/stroke-width/g, "strokeWidth")
      .replace(/stroke-linejoin/g, "strokeLinejoin")
      .replace(/stroke-linecap/g, "strokeLinecap")
      .replace(/stroke-miterlimit/g, "strokeMiterlimit")
      .replace(/fill-rule/g, "fillRule")
      .replace(/clip-rule/g, "clipRule")
      .replace(/clip-path/g, "clipPath")
      .replace(/xmlns:xlink/g, "xmlnsXlink")
      .replace(/xlink:href/g, "xlinkHref")
      // Self-close tags that aren't self-closed
      .replace(/<(\w+)([^>]*?)><\/\1>/g, "<$1$2 />")
      // Ensure self-closing tags end properly
      .replace(/<(path|line|rect|circle|ellipse|polygon|polyline)([^/]*?)(?<!\/)>/g, "<$1$2 />")
  );
}

// ── Lucide-react fallback set ────────────────────────────────────────
// Icons re-exported from `lucide-react` because no custom equivalent exists.
// Keep alphabetised. Adding/removing entries requires regenerating the barrel.
const LUCIDE_FALLBACK = [
  "AlertCircle",
  "AlertTriangle",
  "AlignCenter",
  "AlignLeft",
  "AlignRight",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "ArrowRightLeft",
  "Ban",
  "Braces",
  "Bug",
  "Check",
  "CheckCircle",
  "CheckCircle2",
  "ChevronDown",
  "ChevronLeft",
  "ChevronRight",
  "ChevronUp",
  "Columns",
  "Component",
  "Copy",
  "ExternalLink",
  "EyeOff",
  "Figma",
  "FileSearch",
  "Filter",
  "Frame",
  "GitCommitVertical",
  "GitCompareArrows",
  "GripHorizontal",
  "GripVertical",
  "Group",
  "Image",
  "ImageOff",
  "ImagePlus",
  "Info",
  "Languages",
  "Layout",
  "Link",
  "Link2",
  "Loader2",
  "LogOut",
  "Maximize2",
  "Moon",
  "MoreVertical",
  "MousePointer",
  "MousePointerClick",
  "PanelBottom",
  "PanelRight",
  "Paperclip",
  "Pause",
  "Pencil",
  "Plus",
  "RefreshCw",
  "Repeat",
  "RotateCcw",
  "Save",
  "SkipForward",
  "Square",
  "Tag",
  "ToggleLeft",
  "ToggleRight",
  "Trash2",
  "Type",
  "Variable",
  "WifiOff",
  "WrapText",
  "Wrench",
  "X",
  "XCircle",
  "ZoomIn",
  "ZoomOut",
];

// ── Code Generation ──────────────────────────────────────────────────

function generateIconFile(name, viewBox, jsxInner, isStroke = false) {
  const fillAttr = isStroke ? 'fill="none" stroke="currentColor"' : 'fill="currentColor"';
  return `/**
 * ${name} icon — auto-generated from SVG source.
 * Do not edit manually — regenerate with: node scripts/generate-icons.mjs
 */
import { forwardRef } from "react";
import type { IconProps } from "./_types";

export const ${name} = forwardRef<SVGSVGElement, IconProps>(
  ({ size = 24, className, ...props }, ref) => (
    <svg
      ref={ref}
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="${viewBox}"
      ${fillAttr}
      className={className}
      {...props}
    >
      ${jsxInner}
    </svg>
  ),
);
${name}.displayName = "${name}";
`;
}

const TYPES_FILE = `/**
 * Shared icon prop type — auto-generated.
 * Do not edit manually — regenerate with: node scripts/generate-icons.mjs
 */
import type { SVGProps } from "react";

export interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number | string;
}
`;

function generateBarrel(iconNames) {
  const customExports = iconNames
    .map((name) => `export { ${name} } from "./generated/${name}";`)
    .join("\n");
  const lucideExports = LUCIDE_FALLBACK.map((name) => `  ${name},`).join("\n");
  return `/**
 * Unified icon barrel — auto-generated. Do not edit manually.
 * Regenerate with: node scripts/generate-icons.mjs
 *
 * Custom icons (per-file under ./generated) replace lucide-react where available;
 * lucide-react provides the rest.
 */

// ── Custom icon replacements (${iconNames.length} icons — auto-generated) ──
${customExports}

export type { IconProps } from "./generated/_types";

// ── Lucide-react fallbacks (${LUCIDE_FALLBACK.length} icons — no custom equivalent) ──
export {
${lucideExports}
} from "lucide-react";

// Re-export the LucideIcon type for components that use it for prop typing
export type { LucideIcon } from "lucide-react";
`;
}

// ── Main ─────────────────────────────────────────────────────────────

const GENERATED_DIR = resolve(OUTPUT_DIR, "generated");
mkdirSync(GENERATED_DIR, { recursive: true });

// Write shared types file
writeFileSync(resolve(GENERATED_DIR, "_types.ts"), TYPES_FILE);

// Track unique SVGs (some icons share the same source)
const processedSvgs = new Map(); // path → { viewBox, jsxInner, isStroke }

const generatedNames = [];
const errors = [];

for (const [name, config] of Object.entries(ICON_MAP)) {
  const fullPath = resolve(ICONS_ROOT, config.path);

  let processed;
  if (processedSvgs.has(config.path)) {
    processed = processedSvgs.get(config.path);
  } else {
    try {
      const content = readFileSync(fullPath, "utf-8");
      switch (config.source) {
        case "brand":
          processed = processBrandSvg(content);
          break;
        case "small":
          processed = processSmallSvg(content);
          break;
        case "stroke":
          processed = processStrokeSvg(content);
          break;
        default:
          throw new Error(`Unknown source type: ${config.source}`);
      }
      processed.jsxInner = svgInnerToJsx(processed.inner);
      processedSvgs.set(config.path, processed);
    } catch (err) {
      errors.push(`${name}: ${err.message}`);
      continue;
    }
  }

  const fileContent = generateIconFile(
    name,
    processed.viewBox,
    processed.jsxInner,
    processed.isStroke,
  );
  writeFileSync(resolve(GENERATED_DIR, `${name}.tsx`), fileContent);
  generatedNames.push(name);
}

// Regenerate the unified barrel
writeFileSync(resolve(OUTPUT_DIR, "index.ts"), generateBarrel(generatedNames));

console.log(`Generated ${generatedNames.length} icon files in ${GENERATED_DIR}`);
console.log(`Regenerated barrel at ${resolve(OUTPUT_DIR, "index.ts")}`);
if (errors.length > 0) {
  console.error("Errors:", errors);
  process.exit(1);
}
