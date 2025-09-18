const { defineConfig } = require("cypress");

module.exports = defineConfig({
    env: {
        U0PWD: `${process.env.U0PWD}`
    },

    e2e: {
     experimentalStudio:true,
     defaultCommandTimeout: 10000,

     setupNodeEvents(on, config) {
         on('task', {
             runPgTAP() {
                 const cmd = `pg_prove -h ${process.env.DB_HOST} -U ${process.env.DB_USER} -d ${process.env.DB_NAME} --ext .sql -r ${process.env.PGTAP_TEST_PATH}/seed_utest0.sql`;

                 return new Promise((resolve, reject) => {
                     require('child_process').exec(cmd,
                         { env: process.env },
                         (err, out, errOut) => {
                             if (err) {
                                 console.error(errOut);
                                 return reject(err);
                             }
                             console.log(out);
                             resolve(out);
                         });
                 });
             }
         });
     }
    },
});