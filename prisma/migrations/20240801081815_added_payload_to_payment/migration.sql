-- AlterTable
ALTER TABLE "Payment" ADD COLUMN     "payload" JSONB,
ALTER COLUMN "authority" DROP NOT NULL;
