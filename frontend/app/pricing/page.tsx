import Link from "next/link"
import WithSubnavigation from "@/components/common/with-subnavigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Check, ArrowRight } from "lucide-react"

const plans = [
  {
    name: "Free",
    price: "₹0",
    period: "forever",
    description: "Perfect for getting started with AI tools.",
    cta: "Get Started",
    href: "/signup",
    highlight: false,
    features: [
      "Up to 70 document extractions/month",
      "Course Search access",
      "ATS Resume Matcher access",
      "JSON & Markdown output",
      "Email support",
    ],
  },
  {
    name: "Pro",
    price: "₹999",
    period: "per month",
    description: "For professionals and growing teams.",
    cta: "Start Free Trial",
    href: "/signup",
    highlight: true,
    features: [
      "Unlimited document extractions",
      "All Free features",
      "Priority processing",
      "API access",
      "Advanced export options",
      "Priority email support",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "contact us",
    description: "For large teams with custom needs.",
    cta: "Contact Sales",
    href: "mailto:admin@mnsai.in",
    highlight: false,
    features: [
      "Everything in Pro",
      "Custom integrations",
      "SSO / SAML",
      "Dedicated support",
      "SLA guarantee",
      "On-premise option",
    ],
  },
]

export default function PricingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <WithSubnavigation />

      {/* Hero */}
      <section className="relative flex flex-col items-center text-center px-6 py-20 overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(0,74,173,0.12) 0%, transparent 70%)",
          }}
        />
        <span className="inline-flex items-center gap-2 rounded-full border border-ui-main/20 bg-ui-main/5 px-4 py-1.5 text-xs font-semibold text-ui-main uppercase tracking-widest mb-5">
          Pricing
        </span>
        <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl max-w-2xl">
          Simple, transparent pricing
        </h1>
        <p className="mt-4 text-muted-foreground max-w-lg text-lg">
          Start free, scale as you grow. No hidden fees, no surprises.
        </p>
      </section>

      {/* Plans */}
      <section className="px-6 pb-20">
        <div className="mx-auto max-w-5xl grid grid-cols-1 gap-6 sm:grid-cols-3">
          {plans.map((plan) => (
            <Card
              key={plan.name}
              className={`flex flex-col border ${
                plan.highlight
                  ? "border-ui-main shadow-lg shadow-ui-main/10 ring-1 ring-ui-main"
                  : "border-border"
              }`}
            >
              {plan.highlight && (
                <div className="bg-ui-main text-white text-xs font-bold text-center py-1.5 rounded-t-xl tracking-widest uppercase">
                  Most Popular
                </div>
              )}
              <CardHeader className="pb-2 pt-6 px-6">
                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
                  {plan.name}
                </p>
                <div className="flex items-end gap-1 mt-2">
                  <span className="text-4xl font-extrabold text-foreground">{plan.price}</span>
                  <span className="text-sm text-muted-foreground mb-1">/{plan.period}</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">{plan.description}</p>
              </CardHeader>
              <CardContent className="flex flex-col gap-4 px-6 pb-6 flex-1">
                <ul className="space-y-2.5 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-foreground">
                      <Check className="h-4 w-4 text-ui-main mt-0.5 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  asChild
                  className={
                    plan.highlight
                      ? "bg-ui-main hover:bg-[#003d8f] text-white w-full mt-2"
                      : "w-full mt-2"
                  }
                  variant={plan.highlight ? "default" : "outline"}
                >
                  <Link href={plan.href}>
                    {plan.cta} <ArrowRight className="ml-1.5 h-4 w-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* FAQ note */}
        <p className="text-center text-sm text-muted-foreground mt-10">
          All prices are in INR and exclusive of applicable taxes.{" "}
          <Link href="/resources/blog" className="text-ui-main hover:underline">
            Read our blog
          </Link>{" "}
          for product updates and tips.
        </p>
      </section>

      <footer className="mt-auto px-6 py-8 border-t text-center text-sm text-muted-foreground">
        &copy; {new Date().getFullYear()} mnsAI. All rights reserved.
      </footer>
    </div>
  )
}
