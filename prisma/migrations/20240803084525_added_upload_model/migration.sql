-- CreateTable
CREATE TABLE "Upload" (
    "upload_id" SERIAL NOT NULL,
    "uploaded_file_name" TEXT NOT NULL,
    "user_id" INTEGER NOT NULL,
    "payload" JSONB,

    CONSTRAINT "Upload_pkey" PRIMARY KEY ("upload_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Upload_uploaded_file_name_key" ON "Upload"("uploaded_file_name");

-- AddForeignKey
ALTER TABLE "Upload" ADD CONSTRAINT "Upload_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("user_id") ON DELETE RESTRICT ON UPDATE CASCADE;
