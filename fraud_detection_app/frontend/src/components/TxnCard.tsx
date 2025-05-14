import { CreditCard, TrendingUp, ShieldAlert } from "lucide-react";
import { motion } from "framer-motion";

export type RiskLevel = "low" | "medium" | "high";
interface Props {
  amount: number;
  merchant: string;
  risk: RiskLevel;
}

export default function TxnCard({ amount, merchant, risk }: Props) {
  const Icon =
    risk === "low"
      ? CreditCard
      : risk === "medium"
      ? TrendingUp
      : ShieldAlert;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="ui-card flex items-center gap-4"
    >
      <span className="rounded-full p-2 bg-brand-gray-50">
        <Icon
          size={20}
          strokeWidth={1.8}
          className={`text-risk-${risk}`}
        />
      </span>

      <div className="grow">
        <p className="text-sm font-medium">{merchant}</p>
        <p className="text-lg font-semibold text-brand-blue">
          ₹{amount.toFixed(2)}
        </p>
      </div>

      <motion.span
        key={risk}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className={`px-3 py-1 rounded-full text-xs font-semibold
          bg-[color:theme(colors.risk.${risk}/0.15)]
          text-[color:theme(colors.risk.${risk})]`}
      >
        {risk.toUpperCase()}
      </motion.span>
    </motion.div>
  );
}
