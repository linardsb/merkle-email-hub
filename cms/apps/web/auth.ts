


import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import type { JWT } from "next-auth/jwt";

// Role type generated from auth_roles configuration
export type AppRole = "admin" | "developer" | "viewer";

const VALID_ROLES: AppRole[] = ["admin", "developer", "viewer"];

const API_BASE = process.env.INTERNAL_API_URL || "http://localhost:8891";

/** Matches backend LoginResponse schema */
interface LoginResponseData {
  id: number;
  email: string;
  name: string;
  role: AppRole;
  access_token: string;
  refresh_token: string;
}

function getExpFromToken(token: string): number {
  try {
    const parts = token.split(".");
    if (!parts[1]) return Date.now() + 15 * 60 * 1000;
    const payload = JSON.parse(atob(parts[1]));
    return (payload.exp as number) * 1000;
  } catch {
    return Date.now() + 15 * 60 * 1000; // conservative fallback
  }
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    });

    if (!res.ok) {
      return { ...token, error: "RefreshAccessTokenError" };
    }

    // RefreshResponse only returns access_token (refresh token stays the same)
    const data: { access_token: string } = await res.json();
    return {
      ...token,
      accessToken: data.access_token,
      accessTokenExpires: getExpFromToken(data.access_token),
    };
  } catch {
    return { ...token, error: "RefreshAccessTokenError" };
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60,
  },
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) return null;

        try {
          // Backend LoginRequest expects { email, password }
          const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.username,
              password: credentials.password,
            }),
          });

          if (!res.ok) return null;

          const data: LoginResponseData = await res.json();
          const role = VALID_ROLES.includes(data.role as AppRole) ? data.role : "viewer";

          return {
            id: String(data.id),
            name: data.name,
            email: data.email,
            role,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        return {
          ...token,
          accessToken: user.accessToken,
          refreshToken: user.refreshToken,
          role: user.role,
          userId: user.id,
          accessTokenExpires: getExpFromToken(user.accessToken),
        };
      }

      if (Date.now() < (token.accessTokenExpires as number)) {
        return token;
      }

      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      return {
        ...session,
        accessToken: token.accessToken as string,
        user: {
          ...session.user,
          id: token.userId as string,
          role: token.role as AppRole,
        },
        error: token.error as string | undefined,
      };
    },
  },
});

declare module "next-auth" {
  interface User {
    role: AppRole;
    accessToken: string;
    refreshToken: string;
  }
  interface Session {
    accessToken: string;
    error?: string;
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      role: AppRole;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    role?: AppRole;
    userId?: string;
    accessTokenExpires?: number;
    error?: string;
  }
}
