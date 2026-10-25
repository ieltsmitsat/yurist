const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "/api/v1" : "http://localhost:8000/api/v1");

const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

export function getSavedToken(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("yurist_admin_token") || "";
  }
  return "";
}

export function saveToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("yurist_admin_token", token);
    document.cookie = `yurist_admin_token=${token}; path=/; max-age=604800; SameSite=Lax`;
  }
}

export function removeToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("yurist_admin_token");
    document.cookie = "yurist_admin_token=; path=/; max-age=0; SameSite=Lax";
  }
}

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = getSavedToken() || ADMIN_KEY;
  const authHeaders: Record<string, string> = token
    ? {
        "X-Admin-Key": token,
        Authorization: `Bearer ${token}`,
      }
    : {};

  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
    ...options,
  });

  if (res.status === 401 && typeof window !== "undefined" && window.location.pathname !== "/login") {
    removeToken();
    window.location.href = "/login";
  }

  if (!res.ok) {
    let errorDetail = "";
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = res.statusText;
    }
    throw new Error(errorDetail || `API Error ${res.status}`);
  }
  return res.json();
}

export interface LoginResponse {
  ok: boolean;
  access_token: string;
  token_type: string;
  username: string;
}

export const loginAdmin = (username: string, password: string) =>
  fetchApi<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const checkAuth = () =>
  fetchApi<{ ok: boolean; username: string }>("/auth/me");

// Dashboard
export const getDashboardStats = () => fetchApi<DashboardStats>("/dashboard/stats");
export const getLeadPipeline = () => fetchApi<PipelineItem[]>("/dashboard/pipeline");
export const getRiskBreakdown = () => fetchApi<RiskItem[]>("/dashboard/risk-breakdown");
export const getUsersChart = (days = 30) => fetchApi<ChartPoint[]>(`/dashboard/users-chart?days=${days}`);
export const getInquiriesChart = (days = 30) => fetchApi<ChartPoint[]>(`/dashboard/inquiries-chart?days=${days}`);
export const getRevenueChart = (days = 30) => fetchApi<RevenuePoint[]>(`/dashboard/revenue-chart?days=${days}`);
export const getReferralAnalytics = () => fetchApi<ReferralAnalytics>("/dashboard/referral-stats");

// CRM
export const getLeads = (status?: string, limit = 50) =>
  fetchApi<Lead[]>(`/crm/leads?limit=${limit}${status ? `&lead_status=${status}` : ""}`);
export const getLeadDetail = (id: number) => fetchApi<LeadDetail>(`/crm/leads/${id}`);
export const updateLeadStatus = (id: number, lead_status: string) =>
  fetchApi<{ ok: boolean }>(`/crm/leads/${id}/status`, {
    method: "PUT",
    body: JSON.stringify({ lead_status }),
  });

// Inquiries
export const getInquiries = (risk?: string, limit = 50) =>
  fetchApi<Inquiry[]>(`/crm/inquiries?limit=${limit}${risk ? `&risk_level=${risk}` : ""}`);
export const approveInquiry = (id: number, final_response: string) =>
  fetchApi<{ ok: boolean }>(`/crm/inquiries/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ final_response }),
  });

// Services
export const getServices = () => fetchApi<Service[]>("/services");
export const createService = (data: Partial<Service>) =>
  fetchApi<{ ok: boolean; id: number }>("/services", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateService = (id: number, data: Partial<Service>) =>
  fetchApi<{ ok: boolean }>(`/services/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteService = (id: number) =>
  fetchApi<{ ok: boolean }>(`/services/${id}`, { method: "DELETE" });

// Transactions
export const getTransactions = (status?: string, limit = 50) =>
  fetchApi<Transaction[]>(`/transactions?limit=${limit}${status ? `&payment_status=${status}` : ""}`);
export const updateTransactionStatus = (id: number, payment_status: string) =>
  fetchApi<{ ok: boolean }>(`/transactions/${id}/status`, {
    method: "PUT",
    body: JSON.stringify({ payment_status }),
  });

// Types
export interface DashboardStats {
  total_users: number;
  users_today: number;
  total_inquiries: number;
  inquiries_today: number;
  total_revenue: number;
  pending_payments: number;
  referred_users: number;
  subscribers: number;
}

export interface PipelineItem {
  status: string;
  count: number;
}

export interface RiskItem {
  level: string;
  count: number;
}

export interface ChartPoint {
  date: string;
  count: number;
  [key: string]: string | number;
}

export interface RevenuePoint {
  date: string;
  revenue: number;
  [key: string]: string | number;
}

export interface ReferralAnalytics {
  total_referred: number;
  verified_referred: number;
  conversion_rate: number;
  top_referrers: { full_name: string; telegram_id: number; referral_count: number }[];
}

export interface Lead {
  id: number;
  telegram_id: number;
  full_name: string | null;
  phone_number: string | null;
  language: string;
  lead_status: string;
  free_questions_left: number;
  is_subscribed: boolean;
  created_at: string | null;
}

export interface LeadDetail extends Lead {
  referral_code: string | null;
  referred_by_id: number | null;
  inquiry_count: number;
  referral_count: number;
}

export interface Inquiry {
  id: number;
  user_id: number;
  question_text: string | null;
  stt_transcript: string | null;
  risk_level: string | null;
  risk_score: number | null;
  ai_draft_response: string | null;
  ai_upsell_offer: string | null;
  final_response: string | null;
  status: string;
  created_at: string | null;
}

export interface Service {
  id: number;
  title_uz: string;
  title_ru: string;
  description_uz: string | null;
  description_ru: string | null;
  price: string;
  service_type: string;
  is_active: boolean;
}

export interface Transaction {
  id: number;
  user_id: number;
  user_name: string;
  telegram_id: number;
  phone_number: string | null;
  amount: number;
  payment_method: string;
  payment_status: string;
  transaction_ref: string | null;
  service_title: string | null;
  problem_summary: string | null;
  inquiry_id: number | null;
  appointment_id: number | null;
  created_at: string | null;
}

// Helplines

export interface Helpline {
  id: number;
  category_uz: string | null;
  category_ru: string | null;
  organization_uz: string;
  organization_ru: string;
  phone_number: string;
  description_uz: string | null;
  description_ru: string | null;
  order: number;
  is_active: boolean;
}

export async function getHelplines(): Promise<Helpline[]> {
  const res = await fetch(`${API_BASE}/helplines`);
  if (!res.ok) throw new Error("Failed to fetch helplines");
  return res.json();
}

export async function createHelpline(data: Partial<Helpline>): Promise<Helpline> {
  const res = await fetch(`${API_BASE}/helplines`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create helpline");
  return res.json();
}

export async function updateHelpline(id: number, data: Partial<Helpline>): Promise<Helpline> {
  const res = await fetch(`${API_BASE}/helplines/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update helpline");
  return res.json();
}

export async function deleteHelpline(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/helplines/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete helpline");
}

// Mandatory Subscription Channels & Groups
export interface MandatoryChannel {
  id: number;
  title: string;
  chat_id: string;
  url: string;
  order: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export const getMandatoryChannels = () => fetchApi<MandatoryChannel[]>("/channels");
export const createMandatoryChannel = (data: Partial<MandatoryChannel>) =>
  fetchApi<MandatoryChannel>("/channels", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateMandatoryChannel = (id: number, data: Partial<MandatoryChannel>) =>
  fetchApi<MandatoryChannel>(`/channels/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteMandatoryChannel = (id: number) =>
  fetchApi<{ ok: boolean }>(`/channels/${id}`, { method: "DELETE" });
export const toggleMandatoryChannel = (id: number) =>
  fetchApi<MandatoryChannel>(`/channels/${id}/toggle`, { method: "PATCH" });

// Chats
export interface Dialog {
  user_id: number;
  telegram_id: number;
  full_name: string;
  phone_number: string | null;
  language: string;
  lead_status: string;
  last_message: string;
  last_sender: string;
  last_time: string | null;
  total_messages: number;
}

export interface ChatMessageItem {
  id: number;
  user_id: number;
  telegram_id: number;
  sender_type: "user" | "bot" | "lawyer";
  message_type: string;
  text: string;
  media_url?: string | null;
  created_at: string;
}

export const getDialogs = () => fetchApi<Dialog[]>("/chats");
export const getMessages = (userId: number) => fetchApi<ChatMessageItem[]>(`/chats/${userId}`);
export const sendLawyerMessage = (userId: number, text: string) =>
  fetchApi<ChatMessageItem>(`/chats/${userId}/send`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });

// Settings
export interface BotSettings {
  lawyer_telegram_id: number | null;
  admin_group_id: number | null;
  admin_telegram_ids: string | null;
  inquiry_debounce_seconds?: number;
}

export interface Prompts {
  PERSONA_SYSTEM_PROMPT_UZ: string;
  PERSONA_SYSTEM_PROMPT_RU: string;
  EXPRESS_AUDIT_PROMPT_UZ: string;
  EXPRESS_AUDIT_PROMPT_RU: string;
}

export const getBotSettings = () => fetchApi<BotSettings>("/settings/bot");
export const updateBotSettings = (data: BotSettings) =>
  fetchApi<{ ok: boolean }>("/settings/bot", {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const getPrompts = () => fetchApi<{ prompts: Prompts }>("/settings/prompts");
export const updatePrompts = (prompts: Prompts) =>
  fetchApi<{ ok: boolean; prompts: Prompts }>("/settings/prompts", {
    method: "PUT",
    body: JSON.stringify({ prompts }),
  });

// System Access Management (Lawyers, Groups, Admins)
export interface SystemAccessItem {
  id: number;
  telegram_id: number;
  role: "lawyer" | "group" | "admin";
  name: string;
  description: string | null;
  is_active: boolean;
  created_at?: string;
  lead_topic_id?: number | null;
  contact_topic_id?: number | null;
  payment_topic_id?: number | null;
}

export const getSystemAccessList = (role?: string) =>
  fetchApi<SystemAccessItem[]>(`/settings/access${role ? `?role=${role}` : ""}`);

export const createSystemAccess = (data: {
  telegram_id: number;
  role: "lawyer" | "group" | "admin";
  name: string;
  description?: string | null;
  is_active?: boolean;
  lead_topic_id?: number | null;
  contact_topic_id?: number | null;
  payment_topic_id?: number | null;
}) =>
  fetchApi<SystemAccessItem>("/settings/access", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateSystemAccess = (
  id: number,
  data: Partial<Omit<SystemAccessItem, "id" | "created_at">>
) =>
  fetchApi<SystemAccessItem>(`/settings/access/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteSystemAccess = (id: number) =>
  fetchApi<{ ok: boolean }>(`/settings/access/${id}`, {
    method: "DELETE",
  });

// Organization Profile & Payment Settings
export interface OrgSettings {
  id: number;
  card_number: string;
  card_holder: string;
  contact_phone: string;
  office_address: string;
  working_hours: string;
}

export const getOrgSettings = () => fetchApi<OrgSettings>("/settings/organization");
export const updateOrgSettings = (data: Partial<Omit<OrgSettings, "id">>) =>
  fetchApi<OrgSettings>("/settings/organization", {
    method: "PUT",
    body: JSON.stringify(data),
  });


