import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        Credentials({
            credentials: {
                identifier: { label: "E-post eller användarnamn", type: "text" },
                password: { label: "Lösenord", type: "password" },
            },
            authorize: async (credentials) => {
                const res = await fetch(`${BACKEND}/auth/login`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        identifier: credentials?.identifier,
                        password: credentials?.password,
                    }),
                });
                if (!res.ok) return null;
                const data = await res.json();
                return { id: data.id, email: data.email, name: data.username, role: data.role, accessToken: data.access_token };
            },
        }),
    ],
    pages: {
        signIn: "/login",
    },
    session: { strategy: "jwt" },
    callbacks: {
        jwt({ token, user, trigger, session }) {
            if (user) {
                token.id = user.id;
                token.username = user.name;
                token.role = (user as any).role;
                token.accessToken = (user as any).accessToken;
                token.picture = (user as any).image ?? null;
            }
            if (trigger === "update" && session?.image !== undefined) {
                token.picture = session.image;
            }
            return token;
        },
        session({ session, token }) {
            if (session.user) {
                session.user.id = token.id as string;
                session.user.name = token.username as string;
                session.user.image = token.picture as string | null;
                (session as any).role = token.role;
                (session as any).accessToken = token.accessToken;
            }
            return session;
        },
    },
});
