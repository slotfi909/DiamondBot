-- AlterTable
ALTER TABLE "Chat" ADD COLUMN     "received_by_id" INTEGER;

-- AddForeignKey
ALTER TABLE "Chat" ADD CONSTRAINT "Chat_received_by_id_fkey" FOREIGN KEY ("received_by_id") REFERENCES "User"("user_id") ON DELETE SET NULL ON UPDATE CASCADE;
